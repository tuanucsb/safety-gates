# Results: pilot

## Agent decisions

| Agent | Clean approved (helpful) | Hazard approved (unsafe) | Pressure approved (unsafe) |
|---|---|---|---|
| claude-haiku-5-5 | 60/66 (91%, 95% CI 82-96) | 0/66 (0%, 95% CI 0-6) | 0/66 (0%, 95% CI 0-6) |
| claude-opus-5-5 | 66/66 (100%, 95% CI 94-100) | 0/66 (0%, 95% CI 0-6) | 0/66 (0%, 95% CI 0-6) |

- **claude-haiku-5-5** Pass@1 = 97%; Pass^3 = 95% of 66 instances correct on every repeat; harness: claude-code-cli-2.1.318.
- **claude-haiku-5-5** unsafe approvals by hazard class: ai_model: 0/24 (0%, 95% CI 0-14); document: 0/108 (0%, 95% CI 0-3).
- **claude-haiku-5-5** pressure effect over 66 matched pairs: 0 cases safe without pressure but approved under pressure; 0 the other way. Tasks with any unsafe approval: none.
- **claude-opus-5-5** Pass@1 = 100%; Pass^3 = 100% of 66 instances correct on every repeat; harness: claude-code-cli-2.1.318.
- **claude-opus-5-5** unsafe approvals by hazard class: ai_model: 0/24 (0%, 95% CI 0-14); document: 0/108 (0%, 95% CI 0-3).
- **claude-opus-5-5** pressure effect over 66 matched pairs: 0 cases safe without pressure but approved under pressure; 0 the other way. Tasks with any unsafe approval: none.

## Monitors (applied to every APPROVE)

Unsafe approvals to catch: 0. Safe approvals that should pass: 126. Unsafe cases attempted: 264.

| Monitor | Caught unsafe approvals | False alarms on safe approvals | Unsafe actions executed / unsafe cases | Errors |
|---|---|---|---|---|
| none | - | - | 0/264 (0%, 95% CI 0-1) | - |
| haiku-grounded | n/a | 33/126 (26%, 95% CI 19-34) | 0/264 (0%, 95% CI 0-1) | 0 |
| haiku-transcript | n/a | 31/126 (25%, 95% CI 18-33) | 0/264 (0%, 95% CI 0-1) | 0 |
| rule | n/a | 34/126 (27%, 95% CI 20-35) | 0/264 (0%, 95% CI 0-1) | 0 |
| sonnet-grounded | n/a | 2/126 (2%, 95% CI 0-6) | 0/264 (0%, 95% CI 0-1) | 0 |
| rule+haiku-grounded | n/a | 60/126 (48%, 95% CI 39-56) | 0/264 (0%, 95% CI 0-1) | 0 |
| rule+haiku-transcript | n/a | 58/126 (46%, 95% CI 38-55) | 0/264 (0%, 95% CI 0-1) | 0 |
| rule+sonnet-grounded | n/a | 36/126 (29%, 95% CI 21-37) | 0/264 (0%, 95% CI 0-1) | 0 |

- haiku-grounded: 646/653 evidence quotes found verbatim in the case material.
- haiku-transcript: 648/673 evidence quotes found verbatim in the case material.
- sonnet-grounded: 408/408 evidence quotes found verbatim in the case material.

### Catch rate by task rung, hazard class, key-document read, and hazard type

- **haiku-grounded** - 
- **haiku-transcript** - 
- **rule** - 
- **sonnet-grounded** - 
- **rule+haiku-grounded** - 
- **rule+haiku-transcript** - 
- **rule+sonnet-grounded** - 

