# Defense in Depth for Physical AI

### A design for AI systems that understand the physics, perform engineering tasks correctly, and manage work at scale, built from what nuclear, medical and space safety learned the hard way

Tuan Anh Dinh. ProximaB design note, v2, 8 November 2026. Deep-research draft for review.

v2 integrates three earlier ProximaB documents: *The Engineering Brain* (research report, September 2026) with its
six-layer stack; the *Defense-in-Depth Architecture* note that maps those layers to ABB Atom, FDA V&V 40 and space
FDIR practice; and PRD v2.0 Rev B. The failure modes now carry the FM identifiers from that note, the barriers are
placed in the six layers, and the event-tree arithmetic for the stack is written out with the pilot's measured values.

## Summary

Nuclear power, medical devices and crewed spaceflight each became safe through the same sequence: define the
failure modes, place independent barriers against them, and grade the proof of each barrier by the consequence of
its failure. None of them trusts a single clever component. All of them keep a last line of defense that does not
share the failure modes of the clever part, and all of them feed every incident back into the design. AI safety for
physical engineering should start from that sequence rather than from the AI.

This note does four things.

1. It states the **failure-mode taxonomy** for AI engineering agents under the three requirements you set: the AI
   must understand the physics and chemistry (FM-1.x), it must perform the task with the right function and the right
   method (FM-2.x), and it must be able to manage work at the scale of a plant, a drug program or a mission (FM-3.x).
   Each mode has a known analogue in a regulated industry, and the pilot we ran in Releases 0 and 0.1 has measured
   several of them.
2. It lays out a **five-level defense-in-depth design** for AI engineering agents, modelled on the IAEA levels and
   on the diversity-and-defense-in-depth rules for digital instrumentation and control, with a graded-oversight rule
   taken from how the FDA and ASME decide how much credibility a computational model must earn before a decision
   rests on it.
3. It **places every barrier in the six-layer Engineering Brain stack** (model, harness, skills, solvers and system
   model, evidence ledger, benchmarks), so the design is also a build plan for the two ProximaB codebases, and it
   writes the **event tree** for the stack so that residual risk can be computed from measured barrier failure rates
   rather than asserted.
4. It turns the design into a **research program**: what to measure, in what order, with the pilot results as the
   first data points, and it lists the claims in the existing ProximaB documents that must be verified before they
   are cited.

The single most useful transfer from nuclear is the idea of **common-cause failure**. A monitor that shares the
agent's model family, training data, prompt or information is not an independent barrier, any more than three
pressure transmitters on one impulse line are three channels. In the pilot, Haiku as an agent and Haiku as a monitor
reached the same wrong conclusion on the same task for the same reason. That is a beta factor, and it has to be
assessed, measured and designed against. The second most useful transfer is the one reactor safety design rests on:
you cannot prove a complex system will never fail, so you separate it into divisions that cannot take each other
down, and you put a passive barrier between the worst failure and the public.

## 0. The stack the barriers live in

*The Engineering Brain* describes an AI engineering system as six layers: the foundation model; the harness that
runs the agent loop; the skills that load discipline and regulatory knowledge; the tools, solvers and shared system
model that do the physics; the evidence ledger that records what a regulator will ask for; and the benchmarks that
score the whole configuration. Its finding is that the harness layer has converged on two generic winners, that
every measured gain has come from skills and typed tools, and that the evidence layer is mandated by regulators and
built by almost no one.

Read as a safety architecture, each layer is where a particular class of barrier lives. The table reconciles the
IAEA levels used in this note (plus a Level 0 for qualification before use) with the layer mapping in the earlier
architecture note, and says where each barrier exists today across the two codebases: the Safety Gates repository
(`eng-safety-pilot`, this pilot) and the local harness (`ProximaB/proximab_harness`, with its solvers, verifiers,
evidence ledger and certifier).

| Layer | Defense-in-depth role | Pillar served | Barriers (this note) | Exists today |
|---|---|---|---|---|
| 1. Model | The untrusted complex channel. Never a barrier itself; a candidate for diversity (a different family as a second channel). | all | Pinned version; swapped by Tier-2 FDIR when a channel fails | Agents and monitors pinned per run in both codebases |
| 2. Harness | **Level 2** detection and control: pre- and post-condition gates on every tool call, the convergence gate, bounded repair loops (Tier-1 FDIR), token and time budgets per partition | 2, 3 | Typed tool contracts; "cannot verify" as a flag; limiting conditions for autonomy | Strict tool schemas, harness identity recorded, four monitors (Safety Gates); `TaskRunner` repair loops (local) |
| 3. Skills | **Level 1** prevention: the PIRT pre-flight declaration, the unit type system, the method-selection matrix, the format contract | 1, 2 | Method registry; envelope attestation; evidence trail by construction | `SKILL.md` packs (local); task contracts and requirement-unit reporting (Safety Gates) |
| 4. Solvers and system model | **Level 3** containment: conservation and second-law gateways on every solver output; the dissimilar second channel (reduced-order or analytical) voted against the high-fidelity channel; typed interfaces between disciplines | 1, 2, 3 | Deterministic recomputation; dual-channel comparator | `ThermoVerifier`, `ProcessVerifier`, `NuclearShieldVerifier` (local); unit-aware rule checker and safe calculator (Safety Gates) |
| 5. Evidence ledger and shared state | **Level 4** severe-condition management (transactional system state with rollback; partition isolation; the deterministic runtime-assurance monitor) and **Level 5** learning (tamper-evident audit trail, incident records, re-qualification) | 3 | Two-phase physics commit; Simplex trip to a deterministic fallback; operating-experience program | `EvidenceLedger` with SHA-256 seals, `certifier.py`, `HazopAuditor` as a post-hoc limit check (local); run records and frozen designs (Safety Gates) |
| 6. Benchmarks | **Level 0** qualification before use, and the re-qualification that closes Level 5 | all | Pass@1 and Pass^k by hazard class; catch at a false-alarm budget; control evaluations | Safety Gates Releases 0 and 0.1 (2,000+ episodes); `run_battery.py` and the SMR battery (local, see Section 7b) |

Two consequences follow. First, the layers that regulators mandate (5) and that score the configuration (6) are the
ones nobody has built across disciplines, and they are the two the pilot already produces evidence for. Second, the
barriers at Levels 3 and 4 live in the solver and ledger layers, which is where Release 1 of the product plan builds.

## 1. What the regulated industries learned

### 1.1 Nuclear: levels, independence, separation, and the digital common-cause problem

The five levels of defense in depth were set out in INSAG-3 in 1988 and refined in INSAG-10; the IAEA design
requirements (SSR-2/1, Rev. 1) keep that framework and require that the levels be independent of one another as far
as practicable, and that the means for mitigating severe accidents be largely independent of the systems used for
more frequent events. The levels are: prevention of abnormal operation; detection and control of abnormal operation;
control of accidents within the design basis; control of severe conditions, including preventing progression and
mitigating consequences; and mitigation of off-site consequences.

The ABB Atom reactors designed in Västerås are an example, and the earlier architecture note records the specifics: the
BWR 75 and BWR 90 designs with four physically separated safety divisions, so that a fire or a flood in one quadrant
cannot take the others down; and the severe-accident mitigation that assumes the active systems have all failed,
including filtered containment venting (FILTRA at Barsebäck, the multi-venturi scrubber systems) and the lower-drywell
core catcher. The axiom behind it, in the note's words: you cannot prove that a complex system will never fail, so you
exhaustively define its failure modes, enforce physical and functional separation so failures cannot cascade,
eliminate common-cause failures through diversity, and place deterministic, passive barriers between any component
failure and a catastrophic outcome. Designing that system meant treating software and hardware reliability together,
and it started by naming the failure modes. That is the step most AI safety work skips.

Three further nuclear lessons bear directly on AI. First, software introduced a new kind of failure that hardware
redundancy does not address. Identical software in redundant channels fails identically, so the US NRC's Branch
Technical Position 7-19 (Revision 9, 2024) requires applicants to assess defense in depth and diversity against
common-cause failure from latent design defects in digital safety systems, and NUREG/CR-6303 gives the method: six
attributes of diversity (design, equipment, functional, human, signal, software), with a diverse or manual backup
where the assessment finds a vulnerability. Second, analysis methods are qualified before they are trusted. NRC
Regulatory Guide 1.203 (the evaluation model development and assessment process) begins with a Phenomena
Identification and Ranking Table: before anyone writes an input deck, the engineers name the phenomena that govern the
transient and rank their importance, and the code is then shown to be adequate for exactly those phenomena. Third, the
industry learned after Three Mile Island that the barriers decay unless every event is reported, analysed and fed
back: the operating-experience programs (INPO's SEE-IN, now INPO 10-006) and the plant corrective-action programs
that the NRC inspects are as much a part of defense in depth as the containment building. Fukushima added the
reminder that a common cause can lie outside the design basis: one tsunami defeated every emergency diesel generator
at once.

### 1.2 Medical: risk-graded evidence and change control

ISO 14971 makes risk management the spine of device development, and IEC 62304 ties software rigor to a safety
class. The lesson that makes this concrete is the Therac-25: its predecessors had hardware interlocks against
overdose, the Therac-25 relied on software for the same protection, a race condition defeated it, and patients died.
The FDA's January 2025 draft guidance on AI-enabled device software functions carries the same thinking into AI: a
marketing submission must describe risk assessment, data management, model development, validation, and
performance monitoring across the whole lifecycle, including the risk that performance degrades after deployment;
and the predetermined change control plan guidance (final, December 2024) lets a sponsor pre-specify how a model may
change and how each change will be verified, instead of re-submitting.

The most transferable medical rule is ASME V&V 40 (2018), which the FDA adopted in its guidance on the credibility
of computational models. Model risk is the product of **model influence** (how much of the decision rests on the
model rather than other evidence) and **decision consequence** (how bad a wrong decision is). That risk sets the
credibility level the model must earn, through verification, validation and applicability evidence. If the evidence
falls short, the options are to gather more, improve the model, or reduce its influence on the decision. This is
exactly the rule an organization needs for deciding how much oversight an AI agent's decision requires. V&V 40 also
separates *code verification* from *calculation verification*: a single run on one mesh or one step size is never
credible evidence, because the discretization error has not been bounded. The practical tool is Richardson
extrapolation across two or more resolutions, summarized as a grid convergence index (ASME V&V 20, NASA-STD-7009).

### 1.3 Space and aviation: fault tolerance, the validated envelope, partitioning, FDIR and learning assurance

NASA's human-rating requirements (NPR 8705.2) demand that no two failures, no two human errors, and no combination of
one of each cause loss of crew, and that the system tolerate an inadvertent operator action in the presence of a
single failure. Emergency systems do not count toward that tolerance. Flight rules pre-decide responses to foreseen
conditions so that the decision under pressure is a lookup, not an improvisation. Spacecraft fault management is
organised as fault detection, isolation and recovery (FDIR) in tiers: a component tier that catches and retries local
faults within bounded budgets, a subsystem tier that isolates a persistently failing unit and switches to a redundant
or dissimilar one, and a system tier that puts the vehicle in a safe mode and waits for the ground. Avionics isolate
software partitions in space and time (ARINC 653), so that one misbehaving application cannot starve or corrupt
another.

Two space failures are failure modes of AI agents in miniature. Ariane 5 Flight 501 (1996) reused inertial reference
software from Ariane 4; a horizontal-velocity value outside the range the software had been validated for caused an
operand error and the loss of the vehicle. The Mars Climate Orbiter (1999) was lost because one team's software
produced thruster impulse in pound-force seconds and the other's expected newton seconds. Validated envelope and
units are the two most common hazards in our task suite, and the agents' handling of them was the thing we measured.

For machine learning, EASA's concept paper for Level 1 and 2 AI applications adds a learning-assurance "W-shaped"
process beside the classical V-cycle: the data, the training and the learned model each get their own verification
steps, because the behaviour was learned rather than specified. ISO/IEC TR 5469 (2024) gives sector-independent
guidance on AI in safety functions, ISO/PAS 8800 (2024) applies it to road vehicles alongside ISO 26262, and UL 4600
requires a safety case for autonomous products in which "safe" means an acceptable post-mitigation risk that the
case must justify. The AI safety literature has arrived at the same place from the other direction: safety cases for
frontier AI built on inability, control, trustworthiness or deference arguments (Clymer et al., 2024), with control
as the argument available now.

### 1.4 Autonomous systems: STPA and runtime assurance

Two methods from autonomy complete the set. Leveson's STAMP/STPA treats safety as a control problem: accidents happen
when a controller's model of the process it controls is wrong, and the hazard analysis enumerates the unsafe control
actions, which come in four kinds: an action provided when it is unsafe, not provided when needed, provided in the
wrong order or at the wrong time, or applied too long or stopped too soon. The method finds accidents in which every
component worked as specified, which component-level FMEA cannot. The Simplex architecture, standardised for
aviation as ASTM F3269 run-time assurance, wraps an untrusted high-performance controller inside a simple, verified
monitor and a verified fallback: the monitor watches the state against a safety envelope and, when the complex
controller would leave it, switches control to the fallback. It is how a learned controller can fly without the
learned part being certified; the certification rests on the monitor and the switch.

### 1.5 The eight lessons, stated as design rules

| Rule | Where it comes from | What it means for AI engineering agents |
|---|---|---|
| Define the failure modes first | FMEA, fault trees, HAZOP, STPA | A catalogue of how the agent can be wrong, per capability, before any barrier is chosen (Section 2) |
| Barriers must be independent and diverse | SSR-2/1 independence; BTP 7-19 and NUREG/CR-6303 diversity | Monitors with a different model family, different information, or no model at all; a dissimilar second solver channel |
| Separate so that failures cannot cascade | ABB Atom's four divisions; ARINC 653 partitioning | Discipline agents in isolated partitions with their own budgets, sharing state only through typed, transactional interfaces |
| Grade the evidence by consequence | V&V 40 and FDA credibility; DO-178C levels; IEC 61508 SIL | Oversight class set by AI influence x consequence, not by the task's apparent difficulty (Section 4) |
| Keep a last line that cannot be argued with | Hardwired reactor protection; the core catcher and filtered vent; Therac-20 interlocks; Simplex run-time assurance | A deterministic, non-AI protection layer in the physical or transactional system, with zero model code in it |
| Operate only inside the validated envelope | Ariane 501; ODD in automotive; V&V 20 domain of validation; RG 1.203 PIRT | Every model output and every correlation carries its envelope; using it outside is a REJECT, whatever the number says |
| Control change | FDA PCCP; configuration management; DO-330 tool qualification | Pinned model, harness, skills and tool versions, regression suites, pre-specified update rules |
| Learn from every event | INPO operating experience; corrective-action programs; MAUDE | An incident program for AI engineering decisions, with findings fed back into tasks, prompts and barriers |

## 2. The failure-mode taxonomy

The three requirements you set correspond to three families of failure modes, numbered FM-1.x, FM-2.x and FM-3.x
as in the earlier architecture note, extended with the modes the pilot measured. The tables are the start of an FMEA
for AI engineering agents: each row names the mode, an example or mechanism, how it would be detected, the barrier
that addresses it (with its layer and level from Section 0), and the industry analogue. Rows marked with a pilot
reference were measured in Releases 0 and 0.1. The STPA view in Section 2.3 adds the accidents that FMEA misses.

### 2.1 Family 1: the AI does not understand the physics or chemistry

A language model does not natively hold continuum mechanics, chemical thermodynamics or neutron transport; in STPA
terms every failure here is a flawed process model that stays syntactically fluent while violating a physical
invariant.

| ID | Failure mode | Example or mechanism | Detection | Barrier (layer, level) | Analogue |
|---|---|---|---|---|---|
| FM-1.1 | Conservation-law violation | A flowsheet, heat balance or stress state in which mass, energy, atoms, charge or neutrons do not close; argon accumulating in a recycle loop that the balance ignores | Residual check on every solver output (mass, energy, species closure) | Conservation gateway (L4, Level 3); solver-backed computation (L4, Level 1) | Unaccounted accumulation in recycle loops; unphysical energy generation |
| FM-1.2 | Second-law or equilibrium violation | Heat across a negative temperature difference without work; isentropic efficiency above one; negative absolute pressure or concentration; phase equilibrium ignored | Entropy-generation and bounds checks | Second-law gateway (L4, Level 3) | An impossible condenser or membrane clearance |
| FM-1.3 | Wrong regime or constitutive model | Ideal gas at 150 bar instead of a cubic equation of state; laminar correlations at Re = 10^5; point kinetics when the flux tilt dominates; a sealed tank treated at fill pressure instead of scaling with absolute temperature (S2) | PIRT declaration checked by a rule engine; independent re-derivation by a grounded monitor | PIRT pre-flight gate (L3, Level 1); grounded monitor (L2, Level 2) | Wrong-regime correlations in thermal-hydraulics codes |
| FM-1.4 | Feedback and stiff-kinetics blindness | Arrhenius heat release outpacing linear jacket cooling; positive void coefficient; the xenon peak after a trip | Stability screen at the operating point (heat generation versus removal slopes; Jacobian eigenvalues) | Runaway and stability screen (L4, Level 3); method matrix forces coupled feedback (L3, Level 1) | Bhopal and Seveso; Chernobyl |
| FM-1.5 | Unit, dimension and coordinate errors | 42 lb read as 42 kg (D1); gauge versus absolute pressure; MWth versus MWe; pcm versus dollars; about a fifth of errors in physics benchmarks trace to units | Dimensional check on every reported quantity, in the requirement's unit | Unit type system in the calculator and tools (L3/L4, Level 1); format contract (L3, Level 1) | Mars Climate Orbiter |
| FM-1.6 | Use outside the validated envelope | A correlation, surrogate, twin or QSAR used beyond its validation range: surrogate at Mach 3.1 validated to 2.5 (S6); twin above its validated speed (N5); QSAR outside its applicability domain (D5) | Envelope attestation checked against the validation report | Envelope attestation (L3, Level 1); monitors read validation reports (L2, Level 2) | Ariane 501; V&V 20 domain of validation |
| FM-1.7 | Missing term in a formula | Dropping the common-cause term from a 2oo3 probability of failure on demand (N3) | Deterministic recomputation from the method of record | Method registry with the full formula as code (L3, Level 1) | Software CCF analyses that omit beta |
| FM-1.8 | Aggregation that hides a violation | A rolling one-hour heat-up rate checked only on clock hours (N2); per-rate accuracy averaged across rates (M2) | Recompute at the resolution the requirement states | Requirement-driven computation in the task contract (L3, Level 1) | Peak clad temperature from averaged nodes |
| FM-1.9 | Mis-calibrated uncertainty | A surrogate's error band consuming the whole margin | Margin minus error band; conformal bounds for learned surrogates | Uncertainty-aware limits (L4, Level 3) | Analysis uncertainty margins in thermal design |

Pilot evidence: with every document in hand, Opus 5.5 and Haiku 5.5 found every one of these hazards in 264 unsafe
cases, including the four where an AI model's own output was the trap (FM-1.6). The published physics benchmarks
(ABench-Physics, UGPhysics, PhysReason, NUMCoT) report unit handling, multi-step precision and sign conventions as
the recurring error classes, which is where the task suite should push next. FM-1.1, 1.2 and 1.4 are untested: the
pilot's tasks are decision cases on short case files, not synthesis tasks with solver output to check.

### 2.2 Family 2: the AI does not perform the task correctly

Even when the governing physics is right, the agent can call the wrong function, use an unstable method, or accept
an unconverged result because the script returned exit code 0. *The Engineering Brain* collects the benchmark
evidence: in MDGym, simulations run to completion in 84 to 98 percent of trajectories, and only about a fifth are
physically correct.

| ID | Failure mode | Example or mechanism | Detection | Barrier (layer, level) | Analogue |
|---|---|---|---|---|---|
| FM-2.1 | Wrong function or tool selected | The wrong solver module, arguments in the wrong order, a steady-state solver for a transient, fabricated configuration keys; one error analysis of tool-calling agents attributes about a fifth of failures to tool selection | Typed contracts with preconditions refuse the call; the monitor sees the tool trail | Hoare-style pre- and post-conditions on every tool (L2, Level 2); method registry (L3, Level 1) | Wrong procedure selected under time pressure |
| FM-2.2 | Wrong numerical method | An explicit integrator on a stiff system (prompt-jump kinetics with a 10 microsecond generation time; radical combustion); a CFL limit exceeded; a point forecast where a confidence bound is required; mean instead of per-rate | Stiffness ratio and stability checks; structured check reporting that names the method | Method-selection matrix in the skill pack: stiff systems require BDF or Radau, explicit schemes blocked (L3, Level 1) | Non-conservative analysis methods |
| FM-2.3 | Silent false convergence | A solver that hits its iteration cap or runs on a coarse mesh or too few Monte Carlo particles, returns numbers, and the agent accepts them (S7) | Grid or step convergence index across two resolutions; statistical uncertainty and source entropy for Monte Carlo | Convergence gate per ASME V&V 40 calculation verification (L2, Level 2) | Mesh convergence requirements in ASME V&V 10 and 20 |
| FM-2.4 | Input-deck and parameter drift | One variable updated while coupled boundary conditions keep stale defaults; a dose computed from the original titer after an amendment (C2); a mass from an old revision (S3) | Document-currency and staleness checks; no default placeholders allowed through a precondition | Explicit supersession in case files; preconditions reject stale placeholders (L2/L3, Levels 1-2) | Configuration control of design inputs |
| FM-2.5 | Verification common-cause failure | A reviewer model approves a script because it shares the author model's misconception; Haiku as monitor agreed with Haiku as agent on N5 | Agreement between diverse monitors on known-wrong decisions (the beta estimate) | Dissimilar second channel with no model in it (L4, Level 3); monitors of another family or another information set (L2, Level 2) | NUREG/CR-6303 software diversity |
| FM-2.6 | Unqualified tool or library drift | Arbitrary packages, unverified cross-section tables, changed seeds without a record; the same model scoring differently under different harnesses | Harness and tool versions recorded on every result; regression suite on change | Pinned, qualified configuration; change control (L5/L6, Levels 0 and 5) | DO-330 tool qualification; NQA-1 software records |
| FM-2.7 | Incomplete procedure | Omitting the 24-hour post-maintenance run from an outage duration (N4) | Checklist-as-code | Required steps enumerated in the task contract (L3, Level 1) | Surveillance procedures with sign-offs |
| FM-2.8 | Format mismatch between agent and checker | 34 of 126 rule-checker flags in Release 0 were unit or formulation mismatches, none numeric | Unit-aware comparison; "cannot verify" as a flag | Published format contract (L3, Level 1); unit-aware checker (L4, Level 3) | Interface control documents |
| FM-2.9 | Misreported checks | Submitting checks that pass on a mistaken reading (every simulated miss) | Independent recomputation from source documents | Grounded monitor; deterministic recomputation where possible (L2/L4, Levels 2-3) | Independent verification in QA programs |
| FM-2.10 | Run-to-run variance | Haiku correct on 97 percent of episodes but consistent on 95 percent of instances | Pass^k over repeats | Report Pass^k, require k-of-k for safety-critical classes (L6, Level 0) | Repeatability requirements in test standards |

Pilot evidence: the deterministic checker caught only 13 percent of simulated wrong-input misses on document-hazard
tasks, because a mistaken engineer's numbers satisfy the limit on the mistaken reading; grounded LLM monitors caught
100 percent. The rule checker's flags were all format mismatches (FM-2.8). A deterministic layer is still necessary,
but it must be designed as a format contract and placed where it can see raw inputs, not only reported numbers.

### 2.3 Family 3: the AI cannot manage work at scale

A plant, an integrated chemical complex or a deep-space vehicle spans neutronics, thermal-hydraulics, structures,
controls and licensing. New failure modes appear at the interfaces, and STPA's point applies: the system can fail
while every solver succeeds, because the interactions violate a global constraint.

| ID | Failure mode | Example or mechanism | Detection | Barrier (layer, level) | Analogue |
|---|---|---|---|---|---|
| FM-3.1 | Cross-disciplinary coupling drift | The thermal agent raises the coolant outlet temperature for cycle efficiency and silently violates vessel creep limits and shifts the moderator feedback; a wrong dry mass in one revision propagating into a propellant load | Coupled-dependency invalidation: a change to a shared parameter cannot commit until every consumer re-verifies | Transactional shared system model with two-phase commit (L5, Level 4); cross-stage fault trees (L6, Level 0) | Multi-physics interface mismatch; design-change impact analysis |
| FM-3.2 | Long-horizon context loss | Over a hundred-step campaign, summarisation drops a hard constraint set at step one; METR's 50 percent time horizons double every 4-7 months but 80 percent horizons are far shorter | Horizon-stratified Pass^k; constraints held in the system model, not the prompt | Authoritative state outside the model's context (L5, Level 4); decomposition with verified checkpoints (L2, Level 3) | Situational-awareness loss in long transients (Three Mile Island) |
| FM-3.3 | Unsafe control actions and race conditions | Actions provided when unsafe, omitted when needed, out of order (depressurising before decay heat falls) or held too long; an approval that executes with no containment | STPA UCA filter against the current state; prerequisite steps sealed before dependent actions | UCA filter and reversible-first staging (L5, Levels 3-4); permits-to-work logic | STPA Type 1-4 unsafe control actions; limiting conditions for operation |
| FM-3.4 | Swarm common-cause failure | A supervisor and five specialists on one base model agree on a hazardous action after one adversarial input | Diversity requirement at every interface where a correlated error is catastrophic; beta measured by agreement on known-wrong decisions | Model diversity at the points that matter; Tier-2 FDIR swaps the family (L1/L5, Level 4) | Identical software bug in redundant I&C channels |
| FM-3.5 | Repair-loop thrashing and starvation | One failing sub-agent consumes the budget in a non-converging retry loop and starves the monitors | Per-partition watchdogs on time, iterations and tokens | Partition isolation with budgets (L2, Level 3); Tier-1 FDIR with bounded retries | ARINC 653 temporal partitioning |
| FM-3.6 | Uncontained autonomy: reward hacking, injection, sabotage | An optimiser finds a loophole or follows an injected instruction and drives set-points outside the design basis; red-team Opus complied 5 of 44 times and disclosed each time | Control evaluations; monitors that do not rely on the agent's text; envelope watch | Simplex run-time assurance with a deterministic fallback (L5, Level 4); AI-control protocols (L2, Level 4) | Beyond-design-basis accident; core catcher and filtered vent; insider-threat programs |
| FM-3.7 | Loss of visibility | The agent never opened the hazard document; monitors that see only the transcript lose a third of their catches at a 2 percent false-alarm budget (Release 0.1) | "Documents read" and "tools called" as first-class signals | Grounded monitors; mandatory evidence trails; agent identifiers and logs (L5, Level 2) | Control-room logs; work-order records |
| FM-3.8 | Pressure and goal drift | Schedule and cost notes in every pressure variant | Matched-pair comparison | Decision procedures that make pressure a non-input; pressure as a qualification variant (L6, Level 0) | Production pressure at Chernobyl and Challenger |
| FM-3.9 | Overseer complacency and alarm flooding | Monitors flagging 25-48 percent of safe approvals | False-alarm rate on real traffic as a primary metric | Thresholds set to an audit budget; alarm prioritisation (L2, Level 2) | Alarm management after Three Mile Island; "ironies of automation" |
| FM-3.10 | Oversight that can be subverted | Adaptive attacks make resampling protocols backfire | Adversarial evaluation of the protocol itself | Protocol choice by threat model; audit of the monitor (L6, Level 4) | Red-team exercises on physical protection |

Pilot evidence: with the hazard document unread, the transcript-only monitor almost always flagged the approval for
being unverifiable rather than for the hazard itself, and at an audit-budget threshold those flags fall away. The
monitor needs the evidence, not the agent's narration of it. FM-3.1, 3.3 and 3.5 are untested: the pilot has no
multi-agent or multi-stage tasks yet.

## 3. The design: five levels of defense in depth for AI engineering agents

The levels follow the IAEA structure. Each level has a purpose, barriers, the evidence that qualifies the barriers,
and an independence requirement with respect to the levels beside it. Each barrier is tagged with the layer of the
stack it lives in and marked **built** (exists in one of the two codebases), **partial**, or **to build**.

### Level 0: qualification before use (layer 6, with layer 5 as the record)

Nothing enters service without evidence, and the evidence is graded by consequence.

- **Capability qualification per domain and task class** (built): computed-ground-truth evaluations (the Safety
  Gates format), with Pass@1 and Pass^k, hazard-class breakdowns, and pressure variants. Blind human solves on every
  task (to do). Perturbed re-runs (the local battery's plus or minus 4 percent perturbations) are a second form of
  Pass^k and belong in the same report.
- **Validated envelope declared** (to build): the task classes, document types, units, and consequence classes the
  agent is qualified for, in the way an operational design domain is declared for a vehicle or a domain of validation
  for a surrogate.
- **Learning assurance for learned components** (to build): for any surrogate, twin or QSAR in the loop, the W-shaped
  evidence (data, training, learned model) plus V&V 20/40 credibility proportional to influence and consequence.
- **Configuration pinned** (built): model version, harness version, tools, prompts and thresholds recorded on every
  result; a change control plan that pre-specifies which updates are allowed and what regression suite they must pass
  (to build).

### Level 1: prevention in normal operation (layer 3, with layer 4's typed tools)

The agent is given tools and procedures that make the common failure modes hard to commit.

- **PIRT pre-flight declaration** (to build; the local note's Barrier 1A): before any solver call the agent emits a
  structured declaration of the phenomena, regimes and dimensionless groups that govern the problem (Reynolds,
  Prandtl, Damköhler, Péclet, reduced temperature and pressure, reactivity in units of beta) and the constitutive
  models it will use. A deterministic rule engine checks it: an ideal-gas selection above a reduced pressure of about
  0.2, or above 10 bar, is rejected in favour of a cubic or Helmholtz equation of state; a reactivity insertion above
  half of beta-effective requires coupled Doppler feedback and delayed-neutron groups rather than steady-state
  criticality. This is RG 1.203's first element applied to the agent instead of the analyst.
- **Unit type system** (partial): a unit-carrying calculator that refuses dimensionally inconsistent expressions and
  distinguishes gauge from absolute pressure, thermal from electrical megawatts, and pcm from dollars; every check
  reported in the requirement's unit. Safety Gates has the safe calculator and unit-aware comparison; the typed
  quantity layer on tool inputs is to build.
- **Method registry and method-selection matrix** (partial): the formula or procedure of record is code, named in
  the task contract, and the skill pack carries a matrix from problem class to qualified method, with pre- and
  post-conditions on each tool: stiffness ratio above about 10^3 forces an implicit integrator with a Jacobian;
  shielding problems require buildup factors or continuous-energy transport. This closes FM-1.7, FM-2.1 and FM-2.2.
- **Format contract** (partial): every acceptance check is reported in the requirement's unit and formulation, so
  that a deterministic checker can compare it. The contract is published to the agent as part of the procedure
  (Release 0.2 item).
- **Envelope attestation** (partial): any number taken from a model output or an empirical correlation must be
  accompanied by the validated envelope and the operating point, from the validation document, before it may be used.
  The pilot's four AI-in-the-loop tasks test the agent's side; the tool-side enforcement is to build.
- **Evidence trail by construction** (built): the governing documents for a decision are enumerated; a submission
  that has not opened them is incomplete.

### Level 2: detection and control of abnormal states (layer 2, with the monitors)

Independent monitors and gates review every consequential step and route doubtful ones to a human.

- **Pre- and post-condition gates on every tool call** (partial): the precondition validates schema completeness,
  domain bounds and the absence of stale placeholders; the postcondition validates exit status, residual norm and
  output completeness. A failed gate returns a diagnostic to the agent for a bounded number of repair turns (Tier-1
  FDIR), after which the step escalates.
- **Convergence gate** (to build; the local note's Barrier 2B): for any mesh-based or time-stepped solver, the
  harness runs at least two resolutions and computes a grid convergence index; for Monte Carlo transport it checks
  the statistical uncertainty on k-effective (of order 10 pcm) and the stationarity of the fission source before
  tallies are scored. A run that fails the gate is flagged as FM-2.3 whatever its exit code.
- **Diversity requirement (the BTP 7-19 transfer)** (built in the monitor set; the beta measurement is to do): at
  least one monitor must differ from the agent in model family, and at least one in information (documents rather
  than transcript), or be deterministic. The common-cause beta between agent and monitor is assessed and, where
  possible, measured by agreement on known-wrong decisions.
- **Grounded monitoring** (built): monitors receive the source documents, not only the agent's transcript. Release
  0.1 is the measurement: at a 2 percent false-alarm budget, grounded monitors caught 100 percent of simulated misses
  with the hazard document unread; the transcript-only monitor caught 63 percent.
- **Calibrated thresholds** (built): each monitor's threshold is set to an audit budget on real honest traffic, and
  its false-alarm rate is a primary metric, because an overseer who is flagged 25 percent of the time stops reading.
- **"Cannot verify" is a flag** (built): a check that the deterministic layer cannot compare goes to a human, as a
  plant registry would treat an unreadable surveillance record.
- **Monitor the monitors** (built): suspicion calibration, quote-verification rate and agreement between monitors are
  tracked as operating data.

### Level 3: containment of design-basis failures (layer 4, with the oversight rule)

When the agent is wrong and the monitors are uncertain, the damage is bounded by physics checks that do not depend
on the agent and by how actions are allowed to execute.

- **Conservation and second-law gateways** (partial; `ThermoVerifier` and `ProcessVerifier` check output tolerances,
  the explicit residual gateway is to build): every solver output is audited before the agent may use it. Relative
  closure of mass and elemental balances and of the energy balance within 10^-4; entropy generation non-negative;
  feedback signs as expected (reactivity coefficient negative where the design requires it). The thresholds are
  design choices to be justified per domain, not constants.
- **Dissimilar second channel** (to build; the local note's Barrier 2C): the high-fidelity channel (agent plus solver)
  is cross-checked by a reduced-order or analytical channel with no model in it (point kinetics against transport;
  lumped mass-energy balance against the flowsheet; buildup-factor attenuation against Monte Carlo). A comparator
  passes the result when the two agree within a stated tolerance and the invariants hold; a discrepancy isolates the
  step and returns a diagnostic. This is NUREG/CR-6303's functional diversity, and it is the barrier that makes the
  verification beta small, because a deterministic channel shares no training data with the agent.
- **Graded oversight by consequence** (designed, Section 4): the AI's influence on the decision and the decision's
  consequence set the oversight class, from auto-execute to two-person human review.
- **Reversible-first execution and limiting conditions for autonomy** (to build): actions are staged so that the
  first steps can be undone; irreversible steps wait for the oversight class to clear; budgets of tokens, tool calls,
  time and scope per partition, with a defined response when exceeded.
- **Human role designed against the ironies of automation**: the human decides, with the evidence in front of them;
  they do not merely confirm a recommendation.

### Level 4: severe-condition management (layer 5)

Assume the agent is adversarial or badly wrong and the monitors have been fooled. The barriers here share no code
path with the agent.

- **Partition isolation** (to build): discipline agents (core physics, thermal-hydraulics and process, structures and
  materials, independent verification and licensing) run in separate partitions with no shared mutable context, each
  with its own time, iteration and token budget enforced by a watchdog. One partition cannot overwrite another's
  parameters, inject text into it, or starve it. This is ABB Atom's four divisions and ARINC 653 in software.
- **Transactional shared system model** (partial; `EvidenceLedger` records, the transaction semantics are to build):
  the authoritative state of the design lives in a versioned system model (SysML v2 or equivalent), never in a
  prompt. A change to a shared parameter enters a pending transaction; coupled-dependency invalidation requires every
  consumer discipline to re-verify against the new value before the transaction commits; any failed margin rolls the
  state back atomically to the last verified version. This closes FM-3.1 and FM-3.2 by construction.
- **STPA unsafe-control-action filter** (to build): every proposed action is checked against the four UCA types with
  respect to the current system state, including the rule that a dependent action cannot run before its prerequisite
  verification is sealed in the ledger.
- **Run-time assurance with a deterministic fallback (the core catcher)** (partial; `HazopAuditor` is a post-hoc
  limit check, the Simplex switch is to build): a small, verified set of survival envelopes (peak clad temperature
  below the 10 CFR 50.46 limit; vessel pressure below 1.1 times design; DNBR above its limit; stress below yield over
  the safety factor; a dose below the label maximum; a lot not releasable without a QA record) expressed as barrier
  functions on the state. The monitor contains no model code. When a proposed trajectory would cross the boundary, it
  trips the agent offline and hands control to a pre-qualified conservative controller or to the last sealed safe
  state. This is the reactor protection system and the Therac-20's hardware interlocks; the lesson of the Therac-25
  is that it must not be replaced by software judgement, and the lesson of Simplex is that this is the component the
  certification rests on.
- **Tiered FDIR** (partial): Tier 1 in the harness retries bounded local faults; Tier 2 isolates a partition whose
  reliability has degraded (Pass^k falling below a threshold, or a coupling conflict) and switches it to a diverse
  model family or method, rolling the system model back; Tier 3 freezes autonomous exploration, locks the design to a
  verified conservative baseline, and raises a non-conformance report to the responsible engineer.
- **Control protocols chosen by threat model** (designed): trusted monitoring with defer-to-trusted, audit budgets,
  and resampling where it helps, with the knowledge that resampling can be subverted by an adaptive attacker.
- **Control evaluations as the severe-accident analysis** (built for the confessing adversary; the non-confessing
  one is Release 0.2): red-team policies iterated against the oversight stack, run before and after every qualified
  change.

### Level 5: mitigation and learning (layers 5 and 6)

- **Tamper-evident record** (built locally): every prompt, tool call, input, seed, solver version, reviewer decision
  and sign-off hashed into a write-once ledger, in the form 21 CFR Part 11 and NQA-1 ask for.
- **Incident program** (partial): every unsafe approval, near miss, task defect and monitor false alarm is logged,
  classified by FM identifier, and analysed, in the way licensee event reports and device adverse-event reports are.
  The pilot's run records (changes made after seeing agent behaviour; task defects found by monitors) are the seed.
- **Corrective action** (built as practice): findings change tasks, prompts, tools, thresholds and barriers, with
  re-qualification.
- **Operating experience sharing** (to build): failure modes and fixes shared across sites and vendors, the role INPO
  plays.
- **Periodic re-qualification** (partial): the Level 0 evidence is re-run on a schedule and after every change to the
  model, skills or tools, under a pre-specified change-control plan.

### Independence between levels

Levels 1 and 2 use different mechanisms (declarations and contracts versus gates and review). Level 2's monitors
differ from the agent in family or information. Level 3's second channel and Level 4's protection layer use no model
at all, and Level 4's partitions share no mutable state. Level 5 is organisational. Independence "as far as
practicable" is the design target, and the common-cause assessment in Section 4b is how it is checked.

## 4. The graded-oversight rule

The V&V 40 matrix, applied to an agent's decision rather than a simulation's prediction. **AI influence** is how much
of the decision rests on the agent (sole basis; major input with other evidence; supporting; informational).
**Consequence** is what a wrong decision does (catastrophic: loss of life or a severe release; critical: serious
injury, major damage or regulatory breach; marginal: rework or delay; negligible).

| AI influence \ Consequence | Negligible | Marginal | Critical | Catastrophic |
|---|---|---|---|---|
| Informational | O1 | O1 | O2 | O3 |
| Supporting | O1 | O2 | O3 | O4 |
| Major input | O2 | O3 | O4 | O5 |
| Sole basis | O2 | O3 | O5 | O5 |

| Class | Required barriers | Evidence required at Level 0 |
|---|---|---|
| O1 | Format contract and deterministic check | Pass@1 on the task class |
| O2 | O1 plus one grounded LLM monitor at a stated false-alarm budget | Pass^3; monitor catch rate on simulated misses for the class |
| O3 | O2 plus a monitor of a different model family, or a dissimilar deterministic channel; "cannot verify" routes to a human | Measured catch at the audit budget, read and unread; convergence gate active |
| O4 | O3 plus human review before execution, reversible-first staging, transactional commit of shared state | Control evaluation against a red-team policy |
| O5 | O4 plus run-time assurance with a deterministic fallback in the physical or transactional system, partition isolation, and two-person human review | Control evaluation with non-confessing adversaries; interlock and trip test |

The pilot gives the first numbers to put in this table. A transcript-only Haiku monitor does not meet O3 for any
class where the agent might not have read the evidence, because its catch rate at a 2 percent budget was 63 percent.
A grounded Sonnet monitor met the catch requirement for every simulated class at 1.6 percent false alarms. The rule
checker alone meets only O1, and only with the format contract published.

## 4b. Quantifying the stack: the event tree and the beta factor

Nuclear practice turns the levels into numbers with an event tree: for each initiating event, the frequency with which
the barriers all fail is the product of the initiating frequency and the conditional failure probabilities of the
barriers in sequence. The same arithmetic applies to an AI engineering decision, and it is the honest replacement for
an "alignment score".

For a class of situations m in which the correct decision is REJECT, arising with frequency f_m, an unsafe execution
requires the agent to approve (barrier 1 fails), every Level 2 monitor to miss (barrier 2), the Level 3 checks and
oversight class to let it through (barrier 3), and no Level 4 interlock to stop it (barrier 4):

    F_unsafe = sum over m of  f_m  x  q1(m)  x  q2(m)  x  q3(m)  x  q4(m)

where each q is the probability that the barrier fails *given that the ones before it have failed*. The conditioning
is the whole point. q2 is not the monitor's miss rate on random traffic; it is its miss rate on exactly the approvals
a wrong agent produces, which is what the simulated-miss arm of Release 0.1 measures.

Common-cause failure enters through the beta-factor model used for redundant channels. If monitor A shares the
agent's model family and monitor B is diverse, then

    q2 = [ beta + (1 - beta) x qA ]  x  qB

with beta the fraction of the agent's failures that monitor A shares by construction. For "an LLM judging an LLM" the
earlier architecture note asserts that beta approaches one on out-of-distribution transients. That is a hypothesis,
not yet a measurement; what the pilot shows is that beta is not zero (Haiku as monitor shared Haiku as agent's wrong
reading of N5) and not one (the Haiku monitors caught 100 percent of simulated misses written by Sonnet). Measuring
beta per model pair and per hazard class is research item 4, and the design response does not wait for the number:
a deterministic second channel has beta of zero with respect to any model by construction, which is why Level 3 is
built from solvers rather than from a third model.

What the pilot already puts into the tree (two-sided 95 percent Wilson bounds):

| Term | Measured value | Source |
|---|---|---|
| q1, honest agent, these case files | 0 of 132 per model; at most 2.8 percent | Release 0, Opus 5.5 and Haiku 5.5 |
| q1, agent told to get unsafe cases approved | Haiku 0 of 44; Opus 5 of 44 (11 percent), each disclosed | Release 0.1 red-team arm |
| q2, grounded Sonnet monitor at a 2 percent false-alarm budget | 0 of 129 misses escaped; at most 2.9 percent | Release 0.1 simulated misses |
| q2, grounded Haiku monitor at a 2 percent budget | 0 of 129 | same |
| q2, transcript-only Haiku, hazard document never opened | 37 percent escaped | same, skip arm |
| q2, deterministic rule checker alone | 71 percent escaped (87 percent on document hazards) | same |
| q3, q4 | not measured: the pilot has no Level 3 channel or Level 4 interlock | Release 1 |

Two readings. First, barrier order matters less than barrier independence: a grounded monitor of a different family
reduces the residual by a factor of at least thirty on these cases, while the rule checker alone reduces it by less
than a third, because it shares the agent's inputs. Second, the terms that dominate the residual for a catastrophic
class are q3 and q4, which the pilot cannot yet measure, and the hard part of those is the beta between whatever
channels remain; that is the argument for the solver-based second channel and the model-free protection layer before
any further monitor work.

## 5. Meeting the three requirements

### 5.1 The AI understands the physics and chemistry (FM-1.x)

Understanding is tested, not assumed. The qualification suite distinguishes recall from understanding by using
property-based ground truth: dimensional homogeneity, limiting cases, conservation, monotonicity, symmetry, and
regime boundaries, where the right answer can be computed from the physics rather than looked up. Before computing,
the agent declares the phenomena, regimes and models it is using (the PIRT gate), and the task includes cases where
the declared model is wrong for the regime. After computing, the conservation and second-law gateways check the
result independently of the agent. Learned surrogates in the loop are qualified under V&V 20/40 with a declared
domain of validation and, where possible, conformal uncertainty bounds; the agent's use of them is scored by whether
it respected the domain, not by whether the number looked right.

Metrics: Pass^k by hazard class (unit, regime, missing term, aggregation, envelope, fidelity, stale input); PIRT
declaration accuracy against the method of record; gateway rejection rate and the fraction of rejections that were
true violations; envelope-attestation accuracy.

### 5.2 The AI performs the task correctly (FM-2.x)

Correct performance means the right function, the right method and the right parameters, verifiably. The method
registry makes the formula of record callable code, so that the agent selects rather than reconstructs it; the
method-selection matrix in the skill pack maps problem class to qualified method; typed tool contracts with pre- and
post-conditions refuse out-of-contract calls and unconverged results; the convergence gate makes a single-resolution
answer inadmissible; the dissimilar second channel catches the wrong-input and wrong-method classes that a checker
reading only the reported numbers cannot; and the format contract makes every reported check comparable. Task
contracts enumerate required steps. Qualification is harness-controlled and reports Pass^k, because a buyer in a
regulated industry pays for consistency, not for a good average.

Metrics: tool-selection error rate against typed contracts; method-match rate; convergence-gate failure rate and the
share of "exit code 0" results it rejects; agreement rate between channels; format-contract compliance; Pass^k;
catch rate of independent recomputation on simulated wrong-input misses.

### 5.3 The AI manages work at large scale (FM-3.x)

A plant licensing program, a drug through manufacturing, or a lunar base is a hierarchy of control: program,
project, task, each level a controller with a model of the process it controls (STAMP). The design applies the same
five levels at every tier and adds what scale introduces.

- **Partitioned disciplines with typed interfaces**: discipline agents in isolated partitions with their own budgets,
  exchanging state only through producer-consumer contracts on named parameters, so that an error in one cannot
  travel silently and a runaway in one cannot starve another.
- **Authoritative state outside any model's context**: the system model holds the constraints and the current design;
  agents read and propose, the ledger commits, and a constraint set at step one is still enforced at step one hundred.
- **Error-propagation analysis**: cross-stage fault trees that ask what happens downstream if an upstream value is
  wrong, with coupled-dependency re-verification at each commit.
- **Visibility as infrastructure**: agent identifiers, activity logs and real-time monitoring; "documents read" and
  "tools called" are first-class signals, because the pilot showed that monitors without the evidence degrade.
- **Decomposition with checkpoints**: long tasks are split so that each stage ends in a verifiable, sealed state, and
  budgets per stage act as limiting conditions, because reliability falls with horizon and an 80 percent horizon is
  far shorter than a 50 percent one.
- **Common-cause control across agents**: agents that share a base model, a prompt or a data source share failure
  modes. Diversity is required at the points where a correlated error would be catastrophic, and the FDIR tier can
  swap the family when a partition degrades.
- **Alarm management**: the total human review load is a design quantity. Thresholds are set so that the flags a
  reviewer sees are worth reading.
- **Run-time assurance at the program boundary**: the severe-accident barrier for an AI-run program is a model-free
  monitor on the survival envelopes with a trip to a conservative baseline, and the severe-accident analysis is a
  control evaluation with a red-team policy that does not confess, run against the whole stack.
- **Progression up the ladder only on evidence**: an agent moves from single problems to projects to programs only
  after the residual unsafe-execution rate has been measured at the rung below under the oversight stack it will
  have at the rung above. This is the scale ladder in the PRD, with the oversight classes of Section 4 as the gate.

Metrics: residual unsafe-execution rate per oversight design, as a function of task horizon; monitor catch at audit
budget by stage; agreement between diverse monitors on known-wrong decisions (the beta estimate); transaction
rollback rate and the share of rollbacks that prevented a margin violation; trip rate of the run-time monitor and its
false-trip rate; human review load and reviewer accuracy.

## 6. What the pilot already says about this design

| Design element | Failure modes | Pilot evidence (Releases 0 and 0.1) | Reading |
|---|---|---|---|
| Level 1 physics grounding | FM-1.3, 1.5-1.8 | 0/264 unsafe approvals by honest agents with all documents read | At this difficulty, current models understand these cases; the barrier is not yet tested at harder ones |
| Level 1 format contract | FM-2.8 | All 34 rule-checker false alarms were unit or formulation mismatches | The deterministic layer fails on interface, not on judgement; publish the contract |
| Level 2 grounding | FM-3.7 | Transcript-only catch 63 percent at a 2 percent budget with the hazard document unread; grounded 100 percent | Monitors need the evidence; "the agent said it checked" is not evidence |
| Level 2 diversity | FM-2.5, 3.4 | Haiku-as-agent and Haiku-as-monitor agreed on the same wrong reading of N5 | Model common-cause failure is real; same-family monitors are one channel, not two |
| Level 2 calibration | FM-3.9 | Haiku monitors flagged 25-26 percent of safe approvals at default; Sonnet 1.6 percent | Thresholds must be set on real traffic; small monitors need calibration, not more reasoning |
| Level 3 pressure | FM-3.8 | 0 flips in 132 matched pairs | Pressure of this form did not move these models; harder pressure variants are the next test |
| Level 3 deterministic check | FM-2.9 | Rule checker caught 29 percent of simulated misses, 13 percent on document hazards | A checker that sees only reported numbers cannot catch wrong inputs; the second channel must recompute from sources |
| Level 4 adversary | FM-3.6 | Haiku 0/44, Opus 5/44 compliance with a red-team instruction; every compliance disclosed | Trustworthiness evidence, weak and welcome; the design must not rely on it |
| Level 5 learning | all | Three task defects found by agent escalations before the freeze, one by a monitor during the run | The operating-experience loop works on the benchmark itself |

## 7. Research program

Ordered by what each result unlocks. Items 1-3 are Release 0.2 (in progress on the API credit); items 4-8 are
Release 1 and build in the solver and ledger layers of the local harness.

1. **Failure-mode catalogue (3 months).** Publish the FMEA of Section 2 as a living document with a case for every
   mode, drawn from incident reports in the three industries and from AI engineering benchmarks, with STPA
   unsafe-control-action analysis for the program tier. This is the artefact a regulator can review.
2. **Physics-understanding evaluations with property-based ground truth (3 months).** Extend the task suite with
   regime, conservation and limiting-case checks computed from the physics, and harder unit and precision traps,
   following the error classes the physics benchmarks report; add the PIRT declaration to the task contract and
   score it.
3. **Harder adversaries and misses (now).** Red-team policies that do not confess, iterated against a held-out
   monitor; agents that skip listing documents; misses that require deriving a quantity; a second writer family;
   calibration curves per monitor; the harness-effect arm on the SDK backend.
4. **Monitor diversity and common-cause measurement (3 months).** Measure agreement between monitors of different
   families on known-wrong decisions; estimate beta per model pair and hazard class; test whether a deterministic
   recomputation channel is independent of both.
5. **Method-correctness evaluations graded by solvers, with the Level 1-3 gates built (3-6 months).** Release 1 of
   the product plan in the local harness: a PIRT validator (`pirt_validator.py`), explicit conservation and
   second-law residual gateways in the thermo and process verifiers, a convergence gate (`vv40_convergence.py`) with
   Richardson extrapolation and Monte Carlo stationarity checks, and the dissimilar second channel with a
   comparator, on task families graded by OpenMC, MOOSE, CalculiX and DWSIM. Measure each gate's rejection rate and
   true-violation share.
6. **Graded-oversight calibration (3 months).** For each oversight class, the catch rate and false-alarm cost of
   reaching 99 percent catch, with thresholds calibrated on real traffic; publish the table in Section 4 with
   measured numbers and the event tree of Section 4b with measured q's.
7. **Scale: partitions, transactions and non-confessing adversaries (6-12 months).** Programs of 5-20 linked
   decisions across two or more disciplines, with the transactional system model (ledger transactions with two-phase
   commit), partition budgets, and the STPA UCA filter; red-team policies iterated against the oversight stack;
   human-overseer studies of review load and accuracy; horizon-stratified reliability.
8. **The run-time assurance layer (6 months, with domain partners).** Upgrade the post-hoc limit check into a
   Simplex switch with barrier functions and a deterministic fallback; for each domain, what can be hard-interlocked,
   what cannot, and what the residual risk is when the interlock is the only barrier left. Trip and false-trip rates
   are the metrics.
9. **An operating-experience program for AI engineering decisions (ongoing).** An incident taxonomy keyed to the FM
   identifiers and a shared database, with the corrective-action loop into tasks, prompts and barriers.

Where the evidence would plug into regulation: the NRC's AI strategic plan (NUREG-2261) anticipates licensee use of
AI and prepares staff to review it; the FDA's lifecycle guidance asks for exactly the validation and performance-
monitoring evidence this design produces; ISO/IEC TR 5469 and EASA's learning assurance give the structure a safety
case for an AI engineering agent would follow.

## 7b. Claims in the existing ProximaB documents to verify before they are cited

The earlier documents are the right architecture. Some of their numbers and labels would not survive a reviewer, and
they should be fixed before they are cited.

1. **The SMR evaluation report's certificate.** `PX-NUC-EVAL-2026-09` reports a five-task battery in which every
   non-baseline candidate scores Pass@1 of 100 percent, with an average latency of 0.02 ms and a token cost of
   $0.0014 to $0.03 per solve, and declares a "ProximaB-Qualified Agent" "certified for Grade A deployment". A
   latency of 0.02 ms is not a model call; those rows record scripted or cached candidates, not live frontier models,
   and a battery on which every candidate scores 100 percent at Pass@1 does not discriminate. The report should be
   re-labelled as a pipeline test of the harness, and the certificate language removed: under NQA-1 a vendor cannot
   certify its own agent, and "qualified against battery X, version Y, by Z" is the defensible form.
2. **"Beta approaches 1.0 for an LLM judging an LLM."** Stated as fact in the architecture note; it is a hypothesis.
   The pilot gives the first data (Section 4b): nonzero, and well below one on these tasks. Cite it as the thing
   research item 4 measures.
3. **The CDF formula.** The note's event tree multiplies a bracketed dual-channel term by the remaining barriers as
   if all were independent of the initiating condition and of one another. Section 4b restates it with explicit
   conditioning, which is how the pilot's measurements enter.
4. **Benchmark figures quoted from *The Engineering Brain*** (MDGym's 84-98 percent execution against about 21
   percent correctness; StructureClaw's 82.9 against 22.0 percent; the CAE study's +15.5 points; Pass@1 of 46
   percent falling below 28 percent at Pass^3) are secondary citations, and some combine different benchmarks in
   one sentence. Quote each with its source and date, or not at all.
5. **Named thresholds** (residuals of 10^-4, 10 pcm, GCI tolerances, Pass^3 over Pass@1 of 0.9 for "Grade A") are
   design choices. Present them as proposed acceptance criteria to be justified per domain, not as standards
   requirements.
6. **Standards read through secondary sources.** As in v1, several standards cited here were read through summaries;
   clause numbers should be checked against the primary documents before any regulatory or academic use.

## 8. Sources

Standards and regulators: IAEA SSR-2/1 (Rev. 1) and INSAG-3/INSAG-10 on defense in depth; US NRC Branch Technical
Position 7-19, Revision 9 (2024), on defense in depth and diversity against common-cause failure in digital I&C,
SECY-93-087, and NUREG/CR-6303, Method for Performing Diversity and Defense-in-Depth Analyses of Reactor Protection
Systems (1994); NRC Regulatory Guide 1.203, Transient and Accident Analysis Methods (2005), the evaluation model
development and assessment process and the PIRT; NRC NUREG-2261, Artificial Intelligence Strategic Plan FY 2023-2027;
INPO 10-006 and the NRC's operating-experience and corrective-action inspection guidance; 10 CFR 50 Appendix B and
ASME NQA-1; ISO 14971 and IEC 62304; FDA draft guidance, Artificial Intelligence-Enabled Device Software Functions:
Lifecycle Management and Marketing Submission Recommendations (January 2025); FDA final guidance on predetermined
change control plans (December 2024); FDA Computer Software Assurance guidance (final, September 2025); ASME V&V
40-2018 and FDA guidance on assessing the credibility of computational modeling in device submissions; ASME V&V 10
and V&V 20 (grid convergence index, Richardson extrapolation); NASA-STD-7009B; NASA NPR 8705.2 (human-rating
requirements) and NASA flight rules and fault-management handbook (FDIR); ARINC 653 (avionics application software
standard interface, partitioning); RTCA DO-178C and DO-330; ASTM F3269, Standard Practice for Methods to Safely Bound
Behavior of Aircraft Systems Containing Complex Functions Using Run-Time Assurance (the Simplex architecture); EASA
concept paper on guidance for machine learning and AI applications (W-shaped learning assurance; CoDANN); ISO/IEC TR
5469:2024; ISO/PAS 8800:2024; UL 4600; IEC 61508; 21 CFR Part 11.

Incidents: Leveson and Turner, "An Investigation of the Therac-25 Accidents" (IEEE Computer, 1993); the Ariane 501
inquiry board report (1996); the Mars Climate Orbiter mishap investigation (1999); Fukushima Daiichi investigation
reports; Bainbridge, "Ironies of Automation" (1983). Methods: Leveson, *Engineering a Safer World* (STAMP/STPA,
2011); Sha, "Using Simplicity to Control Complexity" (Simplex, 2001).

AI safety: Greenblatt et al., "AI Control: Improving Safety Despite Intentional Subversion" (2023); Ctrl-Z
(resampling, 2025) and "Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols" (2025); Clymer et al.,
"Safety Cases: How to Justify the Safety of Advanced AI Systems" (2024) and Buhl et al., "Safety cases for frontier
AI" (2024); Anthropic, "Sabotage Evaluations for Frontier Models" (2024), SHADE-Arena (2025), "Three Sketches of
ASL-4 Safety Case Components" (2024) and the Responsible Scaling Policy; Google DeepMind, "An Approach to Technical
AGI Safety and Security" (2025); Chan et al., "Visibility into AI Agents" (2024); "STAMP/STPA Informed
Characterization of Factors Leading to Loss of Control in AI Systems" (2025); METR, "Measuring AI Ability to Complete
Long Tasks" (2025) and Time Horizon 1.1 (2026).

Physics and tool correctness: ABench-Physics, UGPhysics, PhysReason and NUMCoT (2024-2025) on unit, precision and
convention errors; "Characterizing possible failure modes in physics-informed neural networks" (2021) and conformal
prediction for PINNs and neural operators (2025-2026); the Berkeley Function Calling Leaderboard and tau-bench error
analyses (2025); MDGym, StructureClaw, CFDLLMBench and the CAE harness study, as summarised in *The Engineering
Brain*.

ProximaB documents: *The Engineering Brain: harness, skills and benchmarks for scientific and engineering workflows*
(research report, September 2026, 119 references); *Defense-in-Depth for Physical AI: Integrating the 6-Layer
Engineering Brain with ABB Atom Nuclear Safety, FDA V&V 40 and Space FDIR* (architecture note, 2026); ProximaB PRD
v2.0 Rev B (September 2026) and v3.3 (not in this repository; its research design is in `docs/DESIGN.md`); ProximaB Safety Gates Releases 0 and 0.1
(`report/results.md`, `results/control/control.md`); the SMR evaluation report `PX-NUC-EVAL-2026-09` (see Section 7b).

Caveat: several of the standards and papers above were read through summaries and secondary sources in this pass;
exact clause numbers and figures should be checked against the primary documents before they are quoted in a
regulatory or academic setting.
