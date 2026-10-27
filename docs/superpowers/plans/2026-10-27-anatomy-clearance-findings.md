# Anatomy and instrument clearance findings — next implementation input

This is evidence for the next realism milestone, not completed functionality. Active user objective is unchanged.

## Current authoritative geometry

`lens_fluid_solver.gd` generates radius .66 and three layers spanning only .094 model units (thickness/diameter .071). `anatomy_surfaces.gd` corneal diameter is 2.84; anterior membrane center .82 versus corneal apex .932 gives only .112 central clearance. Posterior boundary .50 is also separated from the back of the flat lens particles. Standard pupil radius .98 exceeds lens radius .66. No consistent physical scale currently relates these quantities.

With straight portal-to-tip shafts, adding shaft collision to the current layout would block common existing poses against the iris. The current simplified paths passing tip tests do not prove anatomical shaft clearance. Do not bypass the iris or mark the whole tool collision requirement complete.

## Primary anatomical references consulted

- [Assia and Apple, Side-view analysis of the lens (1992)](https://pubmed.ncbi.nlm.nih.gov/1731729/): postmortem side-view observations report approximately 4.5mm thickness and 9.5mm diameter. This gives thickness/diameter about .47, not the current .071. It is a historical sample, not a universal patient shape.
- [Richdale et al., The Effect of Age, Accommodation and Refractive Error on the Adult Human Eye (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4692191/): 91 adult eyes; dimensions vary with age/refraction/accommodation. The inspected abstract establishes variability, not a single chosen training anatomy. Full table fetch encountered a CAPTCHA; do not invent table values.
- [Xue et al., Panoramic Observation of Crystalline Lenses (2019)](https://onlinelibrary.wiley.com/doi/10.1155/2019/8319027): measured adult lens equatorial diameter roughly 9.2mm and axial thickness roughly 4.2mm in the reported sample, consistent with a substantially thicker lens than the current flat layers.

## Next implementation scope

1. Define one shared parameterized anterior-segment geometry with explicit physical length scale and internally consistent corneal surfaces, chamber depth, pupil/iris, anterior/posterior bag and volumetric lens.
2. Initialize solver rest shapes, rendering, tool portals/action depth, camera and case observation from that same geometry. Preserve old kernel fixtures as explicit legacy defaults, but the actual app must use the improved geometry.
3. Use local geometry tests to show the lens is enclosed by the bag, the chamber has positive clearance, and pupil cases remain connected and identifiable.
4. Add whole-tool shaft/distal-tip contact and incision constraints against the same geometry. Instrument handles must remain outside the eye/microscope working field; the present active-workload capture shows oversized handles intruding into the operative area. Provide valid physical entry/working paths instead of exemptions or arbitrary teleport fixtures.
5. Verify healthy full encounter and injury cases, true pointer input workflow, GPU performance and native build. Geometry-informed behavior still requires specialist evaluation and tissue/device calibration; do not equate dimensions with validated biomechanics.
