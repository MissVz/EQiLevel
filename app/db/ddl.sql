-- 1) enums
CREATE TYPE tri AS ENUM ('low','med','high');
CREATE TYPE mastery AS ENUM ('not_started','in_progress','mastered');
CREATE TYPE rep AS ENUM ('V','A','R','K');

-- 2) core entities
CREATE TABLE students (
  id            BIGSERIAL PRIMARY KEY,
  ext_ref       TEXT UNIQUE,          -- optional external id
  first_name    TEXT NOT NULL,
  last_name     TEXT NOT NULL,
  dob           DATE,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE objectives (
  id            BIGSERIAL PRIMARY KEY,
  unit          CHAR(1) NOT NULL CHECK (unit IN ('A','B','C','D','E')),
  objective_code TEXT NOT NULL,       -- e.g., 'B1'
  description   TEXT NOT NULL,
  strands       TEXT NOT NULL,        -- pipe list: conceptual|fluency|...
  examples      TEXT,
  prereqs       TEXT,                  -- comma list of objective codes
  UNIQUE(unit, objective_code)
);

-- progress rollup per student-objective
CREATE TABLE student_objective (
  id              BIGSERIAL PRIMARY KEY,
  student_id      BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  objective_id    BIGINT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
  mastery_status  mastery NOT NULL DEFAULT 'not_started',
  p_correct       NUMERIC(5,4) NOT NULL DEFAULT 0.0,  -- rolling accuracy 0..1
  attempts        INT NOT NULL DEFAULT 0,
  last_session_at TIMESTAMPTZ,
  CONSTRAINT uq_student_objective UNIQUE (student_id, objective_id)
);

-- sessions
CREATE TABLE sessions (
  id            BIGSERIAL PRIMARY KEY,
  student_id    BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at      TIMESTAMPTZ,
  notes         TEXT
);

-- detailed events within a session
CREATE TABLE session_events (
  id             BIGSERIAL PRIMARY KEY,
  session_id     BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_id     BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  objective_id   BIGINT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
  item_id        TEXT,
  correct        BOOLEAN NOT NULL,
  time_sec       INT NOT NULL,
  representation rep NOT NULL,
  hint_level     SMALLINT NOT NULL DEFAULT 0 CHECK (hint_level BETWEEN 0 AND 3),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_events_student_objective ON session_events(student_id, objective_id);
CREATE INDEX idx_events_session ON session_events(session_id);

-- affect sampling during session
CREATE TABLE affect_log (
  id           BIGSERIAL PRIMARY KEY,
  session_id   BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_id   BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  tstamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
  engagement   tri NOT NULL,
  frustration  tri NOT NULL,
  confidence   tri NOT NULL,
  notes        TEXT
);
CREATE INDEX idx_affect_session ON affect_log(session_id);

-- logged policy adaptations for audit
CREATE TABLE interventions (
  id           BIGSERIAL PRIMARY KEY,
  session_id   BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_id   BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  rule_tag     TEXT NOT NULL,         -- e.g., 'frustration_rising_switch_to_K'
  old_mode     rep,
  new_mode     rep,
  reason       TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- optional: store raw MCP for replay/analysis
CREATE TABLE mcp_snapshots (
  id           BIGSERIAL PRIMARY KEY,
  session_id   BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  student_id   BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  payload      JSONB NOT NULL,        -- the MCPState JSON
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_mcp_session ON mcp_snapshots(session_id);

-- 3) helper view: last 20 rolling accuracy per student/objective
CREATE VIEW rolling_accuracy_last20 AS
SELECT
  e.student_id,
  e.objective_id,
  AVG(CASE WHEN correct THEN 1.0 ELSE 0.0 END) AS p_correct_20
FROM (
  SELECT
    id, student_id, objective_id, correct,
    ROW_NUMBER() OVER (PARTITION BY student_id, objective_id ORDER BY id DESC) AS rn
  FROM session_events
) e
WHERE e.rn <= 20
GROUP BY e.student_id, e.objective_id;

-- 4) function: update student_objective rollup from last 20 events
CREATE OR REPLACE FUNCTION update_student_objective_rollup(p_student BIGINT, p_objective BIGINT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
  UPDATE student_objective so
  SET p_correct =
      COALESCE((SELECT p_correct_20 FROM rolling_accuracy_last20
                WHERE student_id = p_student AND objective_id = p_objective), 0.0),
      attempts =
      (SELECT COUNT(*) FROM session_events
         WHERE student_id = p_student AND objective_id = p_objective),
      last_session_at = now()
  WHERE so.student_id = p_student AND so.objective_id = p_objective;

  -- simple mastery promotion rule; you can add error-profile checks as needed
  UPDATE student_objective so
  SET mastery_status = 'mastered'
  WHERE so.student_id = p_student AND so.objective_id = p_objective
    AND so.p_correct >= 0.80
    AND so.attempts >= 10;  -- guardrail to avoid premature mastery
END; $$;
