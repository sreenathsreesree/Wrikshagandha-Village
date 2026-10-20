# Village Decision Dependency Map (review of A0's open decisions OD-1 … OD-11)

Status: **review document — documentation and decision analysis only.** It decides nothing: every open decision
below keeps its status in `docs/VILLAGE_DESIGN_LOCK_A0.md` §10 (**open**, need the developer), and every
recommendation is the lock's own, restated with its evidence — **a recommendation is not a decision**. It approves no
construction and does not satisfy, replace or shorten the Phase 16 gate (§8 below).

> **Update (2026-10-20): OD-1 is decided** — option (b), Stage A first (D-65; planning sequence only). The review below
> is kept as committed in `a919ceb` (reviewed against `ca45956`, when OD-1 was still open). OD-2 … OD-11 remain open,
> and the Great Tree position and seats stay conditional on OD-2 (a).
>
> **Update (2026-10-20): OD-2 is decided** — option (a), as the layout rule (D-66). OD-3 … OD-11 remain open.

> This review is not the lock's construction step *A1 — Ground, rim, bounds, bands* (lock §11), which still waits for
> Phase 16 and its own approval.

---

## 1. Baseline and scope

- Branch `prototype/organic-world`, reviewed at `ca45956` (A0 — Village World Design Lock: the lock, the layout model
  `tools/sims/sim_village_plan.py`, the blueprint's correction note, D-64). `main` untouched.
- Read: the lock (all sections), `docs/DESIGN_DECISIONS.md` (D-28, D-32, D-45, D-48, D-53, D-54, D-60, D-62, D-64),
  `docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md` (§7 runtime test gates and the Android acceptance policy, §8, the A0
  section, Phase 16), `docs/VILLAGE_BLUEPRINT_A0.md` (§4–§8, including its own five open decisions),
  `docs/PLAYTEST_PACK.md` (S2.11, S6, S7, its open-decisions table) and `docs/ARCHITECTURE.md` (camera bounds).
- The OD wording below is quoted from lock §10; options are not added or reworded. Where the lock lists no options
  (OD-7, OD-10) the table says so.
- **Not an exhaustive register.** This map covers OD-1 … OD-11 only. Other open items in the sources that are not
  numbered OD decisions:
  - the edge bands' art choice (lock §2: "LOCK as a rule, OPEN as an art choice");
  - the optional forest clearing (lock §6, Stage B);
  - the south village houses' number, style and inhabitants (lock §7, A4);
  - frame-rate overlay tooling (lock §9, H4: "adding one is a separate tooling decision");
  - numeric frame-rate, load-time and battery targets (`docs/PLAYTEST_PACK.md` open decision 9).
- **Known constraints carried unchanged:**
  - The Great Tree position (−48, −14) and its three katte seats are **conditional on OD-1 (b) and OD-2 (a)**; if
    either is decided otherwise, they are re-planned and re-checked by the model before A3 (lock §4).
  - The provisional South Ridge area **overlaps the provisional south lane by 1.5 m** — unresolved, to be fixed
    before construction (lock §7).
  - **Seat facing is not checked** by the model; **later-stage areas are not checked against Stage A's paths or
    houses** (lock §12).
  - The camera figures in lock §3 are **model-derived planning estimates**, not runtime measurements.
  - A0 authorises **no construction**; no milestone is marked verified without its required evidence (plan §6, §7).
  - The **Phase 16 exported-Android gate** stays mandatory before any large world expansion (plan §8, Phase 16).

---

## 2. Decision table

**Legend**
- **[S] Source-stated dependency** — written in the cited source.
- **[I] Inferred dependency** — this review's reasoning from the sources; not stated in them.
- **[R] Recommendation only** — the lock's recommendation (lock §10); not a decision.
- The columns "Resolvable by", "Effect if decided otherwise" and "Model re-run?", and the groups in §5, are this
  review's assessment ([I]).

Status for every row: **Open** (lock §10, unchanged). "Resolvable by": **Doc** = documentation and existing evidence
alone; **Visual** = PC and phone visual review; **Cultural** = cultural (and, for practice content, expert) review
(D-54); **Device** = Godot runtime and/or an exported Godot 4.7.x Android build (plan §7 policy).

| OD | Question and options (lock §10) | [R] Lock's recommendation and why | Depends on | Evidence still needed | Resolvable by | Effect if decided otherwise | Model re-run? |
|---|---|---|---|---|---|---|---|
| **OD-1** | Staging — (a) full 128 × 96 m at once; (b) Stage A (x −64 … 32) first | recommended option **(b)** — 1.5× the area, not 3×; measurable before growing further (lock principle 8; plan §8's small-area-first strategy (by analogy [I]) — plan §8 describes the pre-Phase-16 test slice, not post-gate staging) | none | none for the planning choice; device figures come after it (H3, H4) | **Doc** | under (a) the outer west edge, and with it the 4 m west band (lock §2's band rule), would sit at x −96: the Great Tree's move from x −52 to −48, the band clearances, the seats' frame-bottom check and Stage A's area figures all rest on x −64; bake and view cost would be 3×, unmeasured | **Yes** — `bounds`, `band` and possibly `tree`/`seat` lines change |
| **OD-2** | Great Tree occlusion — (a) paths and seats south of the trunk; (b) canopy fade; (c) camera response | recommended option **(a)** — no camera change; the fade needs phone checks (B0.1 finding: the crown hides a player north of the trunk) | none (no dependency stated in the sources). OD-1 and OD-2 are **parallel conditions** on the Great Tree's position and seats (lock §4 [S]); A3 needs OD-2 settled first (lock §11 [S]) | for (a) as a layout rule: none (it is what the plan already does). Whether (a) is *enough* is runtime behaviour: an A3 phone playtest, at both zoom ends (blueprint §4 [S]: at 7 m the tree hides more; tests should cover both ends) | **Doc** for the rule; **Visual/Device** to confirm it holds | (b) is a one-value material change but needs PC/phone dither checks (blueprint §4, option 1); (c) changes camera behaviour and would need its own approval (blueprint §4, option 3: "not proposed"). Either could let paths or seats go north | **Yes** if seats or paths move; no if (a) stands |
| **OD-3** | Stream/waterfall form — (a) flat world, visual cliff; (b) heightmap; (c) terraces | recommended option **(a)** — keeps navigation (max climb 0), camera and budgets | OD-10 for the waterfall [I: OD-10 covers the waterfall's timing]; OD-1 for the stream [I: the stream's timing follows the Stage B plan (lock §11), which rests on OD-1] | how a visual-only cliff and a flat stream read at the game camera (no asset yet); a licensed water recording (lock §8 [S]; AUDIO_ASSETS) | **Doc** for the form's constraints; **Visual** before approval | (b)/(c) break the flat-ground assumption behind navigation (blueprint §5), the camera bounds and the model (its ground is the plane y = 0) | **Yes**, and the model itself would need a terrain height |
| **OD-4** | Lotus Pond ghat side — decided with the pond's layout (Stage B) | **keep open** — depends on the pond's shape and the frame check | the pond's layout [S: lock §10, §6]; OD-10 and OD-1 [I: Stage B land] | the pond's shape; a seated-frame check of the ghat (new plan lines) | **Doc** (geometry), then **Visual** | n/a — by design not decidable now | **Yes**, when the pond and ghat are added to the plan |
| **OD-5** | Vista viewpoints — (a) none, close views only; the South Ridge, if built, is a quiet resting place; (b) a per-spot seated pitch (a camera change E1 left "for a later viewpoint decision") | recommended option **(a) for Stage A**; (b) only as its own, separately approved camera decision later — the current rig cannot frame vistas (lock §3) | none for Stage A. It affects the South Ridge's role and the Stage B waterfall-pool seat, which lock §6 marks OPEN under OD-3 and OD-5 [S] | none for (a): it is today's camera, and D-64 principle (6) already states the constraint (D-64 still lists OD-5 as not decided) | **Doc** for Stage A; (b) would need **Visual/Device** and a camera approval | (b) invalidates lock §3's consequences and the model's seat checks (fixed −42° pitch) | **Yes** for (b) (camera model and §3 table re-derived) |
| **OD-6** | Sanctuary location — (a) reserved north slot, trail from the Hidden Hollow; (b) western forest; (c) behind the falls | recommended option **(a)**, provisional — continues the existing secret chain (D-45's pattern) | OD-7 [I: what it is]; OD-10 and OD-1 [I: the north slot lies in the target, outside Stage A]; for option (c), the falls [S: option (c) explicitly names the falls]; its relationship to OD-3 and OD-10 [I] | the sanctuary's meaning (OD-7); Stage B layout | **Doc**, after OD-7 | moves the provisional `sanctuary` area | **Yes** (target check only) |
| **OD-7** | Sanctuary meaning and reward — no options listed | **open** — no source yet; D-54 review for any practice content | D-54 review for any practice content [S: lock §10]; gates OD-6 [I] | a written source/concept from the developer; cultural (and expert, for practice content) review; reward rules consistent with principle (1) and the once-ever pattern (D-21/D-22, D-45) [I] | **Cultural** (+ Doc) | n/a | No (unless it adds placed props) |
| **OD-8** | Navigation regions — (a) one; (b) one per zone | **decide after H3** — no device data | H3 [S: lock §10]; OD-1 [I: how much area is baked; H3 measures "today's build first … then Stage A", lock §9] | H3: run-to-walkable time on an exported 4.7.x build (S2.11, S7.2) — today's build as the baseline, then Stage A ground | **Device** | (b) changes Stage A's scene structure at A1; no layout change | No |
| **OD-9** | Cultural review of the shrine details — (a) review before A3; (b) generic details | recommended option **(a)** — respectful depiction (D-54's review principle) | A3 needs it settled first [S: lock §11, §4] | for the review itself: a reviewer and the preview asset's kalava threads and clay diyas | **Doc** for choosing to review; **Cultural** for the outcome | (b) changes the asset only; the triangle budget (H2) is re-checked [I] | No |
| **OD-10** | Long-term target and waterfall timing — no options listed | **[R]** keep 128 × 96 m; waterfall in Stage B — the heart before the far destination | OD-1 [I: Stage B follows Stage A, lock §2]; device evidence on Stage A [I] | H3/H4 on Stage A before committing to 3× the area | **Doc** for "waterfall not in Stage A"; **Device** for the target size | a different target moves the `target` bounds and later-stage areas | **Yes** (Stage A must stay inside the target) |
| **OD-11** | Edge backdrop beyond the rim — (a) visual treeline beyond the rim (A1); (b) bands only | recommended option **(a)**, decided at A1 with screenshots — the frame reaches ~22 m sideways (lock §3, a model estimate) | screenshots at A1 [S: lock §10]; OD-1 [I: where the rim is] | PC and phone screenshots at the Stage A rim; the backdrop's cost within H1 | **Visual** (+ Device for cost) | none for the plan geometry (the backdrop is outside Stage A) | No (the model does not check beyond the rim) |

---

## 3. Dependency relationships

**What depends on OD-1:**
- **[S]** the Great Tree's position (−48, −14) and its three katte seats (lock §4: "conditional on OD-1 and OD-2").
- **[I] directly:** OD-8 (how much ground is baked), OD-10 (the target and the waterfall are framed as Stage B,
  "after Stage A is accepted on the phone", lock §2), OD-11 (where the rim is; "decided at A1").
- **[I] through OD-10:** OD-4 and OD-6 (their land lies only in the target), and OD-3 for the waterfall's timing.
- **[I] directly, for the stream:** OD-3's stream timing follows the Stage B plan (lock §11), which rests on OD-1.
- **Not dependent on OD-1:** OD-2 (a parallel condition, not a dependent), OD-5, OD-7, OD-9.

```
Great Tree position and katte seats (lock §4)
  ├── conditional on OD-1 (b) ................................ [S] lock §4
  └── conditional on OD-2 (a) ................................ [S] lock §4   (OD-1 and OD-2 are parallel conditions)
A3 — Great Tree, katte seats, tree road
  └── needs OD-2 and OD-9 settled first ...................... [S] lock §11

OD-1 staging
  ├── OD-8 navigation regions ................................ [I] area baked
  │     └── decided after H3 ................................. [S] lock §10
  ├── OD-10 target and waterfall timing ...................... [I] Stage B follows Stage A (lock §2)
  │     ├── OD-3 stream/waterfall form ....................... [I] waterfall timing only
  │     ├── OD-4 lotus ghat .................................. [I]; also the pond's layout [S] lock §10
  │     └── OD-6 sanctuary location .......................... [I]; option (c) names the falls [S]; its tie to OD-3/OD-10 [I]
  ├── OD-3, stream timing (Stage B plan, lock §11) ........... [I]
  └── OD-11 edge backdrop .................................... [I] where the rim is
        └── decided at A1 with screenshots ................... [S] lock §10
OD-7 meaning and reward
  ├── D-54 review for any practice content ................... [S] lock §10
  └── OD-6 location .......................................... [I]
OD-5 viewpoints
  ├── the South Ridge's role: a quiet resting place .......... [S] lock §6
  │   (its 1.5 m overlap with the south lane is settled when the South Ridge (OD-5) and A4 are laid out [S] lock §7;
  │    OD-5 (a) alone does not resolve it)
  └── the Stage B waterfall-pool seat, OPEN under OD-3 and OD-5 ... [S] lock §6

Measurements (desktop baselines and device evidence) and the Phase 16 gate
  desktop, now: W1 software-rendering baselines (relative only; not Android figures) ........ [S] lock §9
  during the device playtest sessions on an exported Godot 4.7.x build (the testing that leads to and includes the
  Phase 16 gate):
    └── baseline load time on today's build — H3's baseline ... [S] lock §9 ("today's build first"); PLAYTEST_PACK
        S2.11 (M01.6) and S7 (risk A8: "Phase 01 test, Phase 16")
  Phase 16 passes on Android (mandatory before any large world expansion) ....... [S] plan §8, Phase 16
    └── A1 … A4, each separately approved (lock §11)
          └── Stage A measurements (lock §9, §11):
                ├── H1 views — desktop software rendering, relative (not device evidence)
                └── H3 on Stage A ground and H4 — exported build on the phone (device evidence)
```

- **OD-1 is the root** of the inferred chains; nothing it depends on is stated in the sources.
- **No OD depends on OD-5.** It affects the South Ridge's role and the Stage B waterfall-pool seat (OPEN under OD-3
  and OD-5, lock §6 [S]); OD-5 (a) does not resolve the South Ridge overlap.
- **Phase 16 is not passed.** The baseline device figures can be gathered during the playtest sessions that lead to the
  gate; the Stage A figures that OD-8 and OD-10 ultimately need come only after Phase 16 and A1. No decision here
  substitutes for the gate.

---

## 4. Evidence and validation requirements

| Evidence | Needed by | Exists? | Procedure |
|---|---|---|---|
| Model geometry (bounds, clearances, seat frames, reveal) | OD-1, OD-2 re-planning; OD-4, OD-6, OD-10 plan changes | yes, for the current plan (`sim_village_plan.py`, run by `tools/run_all.sh`) | re-run after any plan-block change; it checks geometry only |
| Seat facing | the katte seats (§4) | **no** — the model records yaw but does not check it. A manual check of the three yaws against the trunk during the A0 audit found them consistent; that is a **manual inference**, not a documented model check | a future model check (not proposed here), or a hand check recorded with A3 |
| Later-stage areas against Stage A paths/houses | the South Ridge overlap | **no** — unchecked by the model | resolve the overlap in the plan, then re-run |
| Forest-strip gap ≥ 3 m between collider edges (blueprint §5) | the strip threshold (A2) | **not validated** — `sim_village_plan.py` does **not** assert the 3 m rule. A manual calculation during this review, from the tree positions in `scenes/world/Meadow.tscn` and the trunk-collider radii hard-coded in the model (`TRUNK_R`, times each tree's scale), gives **3.83 m** between `ForestWest5` and `ForestWest6` — the narrowest calculated trunk-collider gap across the path in both tree rows (the next is 5.66 m); no other prop with a collider lies within 6 m of the path. A calculated figure is not model validation | a baked Godot navigation mesh at A2 shows the actual walkable corridor (agent radius 0.35 m each side) |
| Occlusion at both zoom ends | OD-2 | desktop preview capture only (B0.1) | phone playtest at A3 (exported build) |
| Shrine-detail review | OD-9, A3 | no | cultural reviewer (D-54) |
| Sanctuary concept and review | OD-7, then OD-6 | no | developer's source; cultural/expert review |
| Screenshots at the rim | OD-11 | no (Stage A not built) | PC and phone at A1 |
| View cost (H1), Great Tree budget (H2) | A1–A3, OD-11, OD-9 (b) | H1: desktop software-rendering baselines only (W1, `ca9b3b0`, relative; not Android figures). H2: the Great Tree preview measures 11,064 of its 12,000-triangle budget (the B0.1 measurements in the master plan) — a triangle count, not a device performance figure | `measure_render.gd`, `check_organic_assets.gd` |
| Navigation bake on device (H3) | OD-8, OD-10 | **no** | S2.11 / S7.2 on an exported Godot 4.7.x build: today's build during the playtest sessions leading to Phase 16 (PLAYTEST_PACK S2.11, S7), Stage A only after Phase 16 and A1 |
| Device frame rate (H4) | OD-10, Stage B | **no** | S7.1 with the remote debugger (PLAYTEST_PACK open decision 4) |
| Phase 16 checklist on Android | all construction | **not passed** | PLAYTEST_PACK sessions on an exported build |

Static checks (the model, `check_project.py`, `check_pack.py`, `run_all.sh`) are not a Godot runtime test and not an
Android acceptance test.

---

## 5. Groups

This grouping is this review's assessment ([I]). Every OD stays **open** until the developer approves it.

**A. Safe to resolve now** (existing requirements and evidence support the lock's recommendation; no unobserved
runtime behaviour has to be guessed):
- **OD-1 — recommended option (b).** Follows from lock principle 8 and plan §8's small-area-first strategy (by
  analogy [I]: plan §8 describes the pre-Phase-16 test slice, not post-gate staging); it is the smaller step. Approving it would lift the OD-1 condition on lock §4. It would authorise no construction.
- **OD-2 — recommended option (a), as the layout rule.** It is what the plan already does and needs no camera or
  material change; approving it would lift the OD-2 condition on lock §4. Whether it is *sufficient* is confirmed
  later on the phone (A3); option (b) stays the documented fallback with its own visual check. (It could equally be
  placed in group B.)
- **OD-5 — recommended option (a), for Stage A only.** It is today's camera; D-64 principle (6) already states the
  constraint. It would not settle (b) for later, and it does not fix the South Ridge overlap.
- **OD-9 — recommended option (a), the process choice only** (review before A3). The review's outcome is in group B.

**B. Prepare now, decide later** (document criteria and procedures; approve when the evidence exists):
- **OD-3** — the constraints of option (a) are documented; decide before Stage B layout, after a visual check of a
  cliff/stream look and with a licensed recording for its sound.
- **OD-7** — needs the developer's concept and cultural (and expert) review.
- **OD-9 outcome** — the cultural review of the kalava threads and clay diyas, before A3.
- **OD-11** — needs rim screenshots (PC and phone) at A1 and the backdrop's cost within H1.

**C. Blocked by prerequisites**:
- **OD-4** — by Stage B, OD-10 and the pond's layout.
- **OD-6** — by OD-7 and OD-10 (and the waterfall for option (c)).
- **OD-8** — by H3 on an exported build (the Phase 16 export environment) and OD-1.
- **OD-10** — by OD-1 and device evidence (H3/H4) on Stage A.

---

## 6. Unresolved risks

1. **South Ridge / south lane overlap (1.5 m)** — unresolved; must be fixed before construction; the model cannot
   catch it today.
2. **Seat facing unchecked** — the katte seats' yaws were found consistent with facing the trunk by a manual check
   (a manual inference), but the model does not assert it.
3. **Occlusion sufficiency** — OD-2 (a) is untested at Stage A geometry and at the 7 m zoom end.
4. **Camera figures are model estimates** (lock §3); none is a runtime measurement.
5. **Device performance unknown** — H3/H4 unmeasured; Stage A's 1.5× area and the target's 3× have no device data.
6. **Phase 16 not passed** — no construction can start, whatever is later decided.
7. **Documentation inconsistencies found (reported only; no source document is changed by this review):**
   - **O-12 / D-32.** Lock §2 cites O-12 ("as it does today (O-12)") without noting that D-32 closed it (bounds clamp
     the camera's focus, not its view); the behaviour it describes — the ground's end can show — matches D-32.
     `docs/ARCHITECTURE.md:133` is stale: it still describes O-12 as an open question.
   - **Construction steps.** The blueprint's A1–A5 list (§7) is a suggested split, introduced by "e.g." ("e.g. A1
     ground + rim + camera bounds; … A3 Great Tree placement with collider and fade decision; A4 north village; A5
     pond and forest loop"). The lock's §11 gives a different sequence (A1–A4, with the north village in Stage B).
     The blueprint's correction note says the lock supersedes it only "where the geometry … shows it can't work"; it
     does not mention the step list, so the two documents differ and neither is stated to replace the other here.
   - **Great Tree visibility from the Village Square.** By the lock's model-derived estimates (not runtime
     measurements): walking north at the default arm, the crown is in the frame by 12 m south of the trunk (lock §4;
     the model's centre-line estimate is about 13 m). The square's centre is about 19.1 m from the trunk, so the crown
     is estimated to be out of frame there; the square's north-west edge is about 11.1 m from the trunk, so it is
     estimated to be in frame by that edge (lock §4: "the crown is in view as the player leaves the square"). Lock
     §3's general sentence ("seen from the square" does not hold) is refined by §4. Blueprint §6's
     exception ("the Great Tree is the one exception (visible from the square)") concerns render distance
     (`visibility_range_end`), not camera framing; whether the exception is still needed should be reviewed at A3.
     The blueprint's correction note covers "seen from the square" in its §2 and §4, not §6's wording.
   - **The blueprint's five open questions (§8)** against the OD list:
     - Q1 (canopy fade, or design around it) — matches OD-2, options (b) and (a).
     - Q2 (one navigation region or one per zone) — matches OD-8 (but see the next item).
     - Q3 (Hill View: visual rise or real terrain) — **partial**: the vista side is covered by OD-5 (lock §3: not
       buildable as a vista); the terrain component only partly matches OD-3 option (b), which OD-3 frames for the
       stream and waterfall, not a hill.
     - Q4 (stream and waterfall: in Stage A, or later) — **partial**: OD-3 covers the stream/waterfall form and OD-10
       the waterfall's timing; the stream's timing is not covered by any OD (lock §11 plans the stream for Stage B).
     - Q5 (Ruins secret: keep reserved, or schedule) — **partial**: OD-6 option (a) proposes the reserved slot for the
       sanctuary (lock §8) but does not resolve when or whether it is scheduled; lock §11 lists the sanctuary in
       Stage B "if approved (OD-6, OD-7)".
   - **Navigation options.** Blueprint §5 lists a coarser navigation cell (0.3 m) outside the village as an option
     alongside one region per zone; lock OD-8 lists only (a) one region and (b) one per zone. The coarser-cell option
     is absent from OD-8. This is a source inconsistency; this review does not add the option to OD-8 or choose
     between the documents.

---

## 7. Recommended next action

**The developer decides OD-1** (staging; the lock's recommended option is (b)). It is the root of the dependency
chains, needs only documentation, carries no runtime guess, and would remove one of the two conditions on the Great
Tree's planned position. If the developer approves it, the decision would be recorded as a design decision, OD-1
marked decided in lock §10, and `sim_village_plan.py` re-run (no plan change is expected for option (b)). OD-2 —
recommended option (a) — is the natural second decision. Neither starts construction.

Outside the village work, the project's critical path stays the **Phase 16 exported-Android playtest**
(`docs/PLAYTEST_PACK.md`): it is where the baseline device evidence comes from, and it must pass before any large world
expansion.

---

## 8. What this document does not do

It approves no construction, decides no open decision, marks no milestone verified, changes no coordinate, plan line,
model check or design status, and does not satisfy the Phase 16 gate. Large world expansion still waits for Phase 16
to pass on an exported Godot 4.7.x Android build (plan §7, §8).
