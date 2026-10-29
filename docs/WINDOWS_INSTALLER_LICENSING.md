# Windows candidate redistribution review

29 October 2026: preliminary artifact review, **not redistribution clearance**.
Only a private qualification candidate was constructed. No public installer,
release, tag or binary PR artifact is produced. The builder marks every output
`distribution_allowed=false` and includes a not-for-distribution notice.

## Findings from actual artifacts

| Component | Observed evidence and outstanding obligation |
| --- | --- |
| PsyCoLab source | No top-level LICENSE at reviewed main `3d7ee02`. The owner must choose/document distribution rights, contributor coverage and bundled material rights before public redistribution. Do not infer a licence from public GitHub access. |
| conda-standalone 25.7.0 h57928b3_0 | Container metadata says `LicenseRef-CondaStandalone`. Extracted notices include the BSD-3-Clause recipe licence and third-party licence inventory. The builder retains them. The executable bundles Conda, Python, PyInstaller and dependencies: review their actual notices and applicable exceptions individually. A project-level BSD label alone is insufficient. |
| Approved interpreter packages | Metadata inspected for all 19 artifacts, including Python-2.0, bzip2, MIT, 0BSD, SQLite blessing, Zlib, Apache-2.0, TCL, public-domain/zone data, BSD and Microsoft runtime terms. Some archives have licence information outside `info/licenses/`; absence there does not imply permission or absence of obligations. Original artifacts remain complete. |
| Microsoft binaries | `ucrt` identifies `LicenseRef-MicrosoftWindowsSDK10`; `vc14_runtime` and `vcomp14` identify `LicenseRef-MicrosoftVisualCpp2015-2022Runtime` and contain licence texts. Verify the distributor's actual rights and exact permitted payload/terms, including standalone provisioner's bundled binaries. Do not infer redistribution rights from conda-forge availability. |
| Runtime/build wheels | Metadata and notice paths inspected for all 25 actual profile artifacts. NumPy, Matplotlib, Pillow, fonttools, pip and setuptools can contain additional bundled component notices; review the complete wheel, not just its top-level classifier. Keep notices/copyright/disclaimers and any applicable notice/source requirements. |
| Windows/.NET Framework | Use the supported Windows-installed framework; do not copy framework binaries into the package. University IT must qualify the supported Windows image. |

The runtime/build set is contourpy, cycler, fonttools, kiwisolver, linkify-it-py,
markdown-it-py, matplotlib, mdit-py-plugins, mdurl, numpy, packaging, pillow, pip,
platformdirs, pyglet, Pygments, pyparsing, python-dateutil, rich, setuptools, six,
textual, typing_extensions, tzdata and wheel. Versions, filenames and hashes
remain authoritative in `profile.json`; development-only pytest, pluggy,
iniconfig and colorama are not shipped by this builder.

## Required before redistribution

- [ ] Owner records PsyCoLab licensing and contributor/asset permissions.
- [ ] Produce a complete binary component/notice inventory from the exact approved
  output, including native libraries embedded in wheels and standalone Conda.
- [ ] Resolve Microsoft SDK/runtime redistribution eligibility and restrictions
  with the institution/distributor using the actual package licence texts.
- [ ] Review bundled licences, exceptions, attribution/NOTICE/source obligations;
  include an accessible complete third-party notices directory in the final package.
- [ ] Record institutional approval of artifact sources, delivery/channel terms
  and any signature/trust or software supply-chain requirements.
- [ ] Authenticate/sign the approved package and manifest; confirm Windows prompts
  and managed-device policy without instructing students to bypass safeguards.
- [ ] Build from a clean reviewed source revision, retain hashes and notices,
  qualify independent installation and obtain maintainer release approval.

The candidate builder intentionally has no `--release` switch. Rights approval
is not supplied by a hash, successful install, permissive dependency name or
software test. Packaging does not certify any laboratory apparatus.

Primary references checked during review:
[conda-standalone](https://github.com/conda/conda-standalone),
[upstream licence](https://github.com/conda/conda-standalone/blob/main/LICENSE),
[Microsoft redistribution guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files),
[Microsoft licence terms](https://visualstudio.microsoft.com/license-terms/).
The artifact-local licence texts take precedence over summary labels.
