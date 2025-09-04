// strands and affect enums
export type Strand = 'conceptual'|'fluency'|'strategic'|'adaptive'|'disposition';
export type Tri = 'low'|'med'|'high';
export type Vark = 'V'|'A'|'R'|'K';

// style profile
export interface StyleProfile {
  V: number; A: number; R: number; K: number; // 0..1 proportions (sum ~ 1.0)
}

// what the learner is working on
export interface LearnerState {
  unit: 'A'|'B'|'C'|'D'|'E';
  objective: string;                     // e.g., "B1"
  strand_focus: Strand[];                // e.g., ['conceptual','fluency']
  prereq_mastered: boolean;
  style_profile: StyleProfile;
  p_correct_rolling: number;             // 0..1 rolling accuracy
}

// affect and engagement
export interface AffectState {
  engagement: Tri;
  frustration: Tri;
  confidence: Tri;
  notes?: string;
}

// last interaction snapshot
export interface LastInteraction {
  rep: Vark;                             // last representation used
  hint_level: 0|1|2|3;                   // 0 = none, 3 = maximal
  error_pattern?: string;                // heuristic tag (e.g., 'miscount', 'ten-ones confound')
  time_sec: number;
}

// tutor policy suggestion for the next turn
export interface NextActionPolicy {
  rep_candidate: Vark;                   // next modality suggestion
  scaffold: string;                      // e.g., "manipulatives→equation"
  difficulty_delta: -1|0|1;              // easier, same, harder
  goal_check_in: boolean;                // quick self-check/metacog prompt
  fluency_burst?: boolean;               // short low-stakes rehearsal if needed
}

// root MCP object for a single turn
export interface MCPState {
  learner_state: LearnerState;
  affect_state: AffectState;
  last_interaction: LastInteraction;
  next_action_policy: NextActionPolicy;
  timestamp: string;                     // ISO
  session_id: string;
  student_id: string;
}
