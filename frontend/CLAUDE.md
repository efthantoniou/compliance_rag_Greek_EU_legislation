@AGENTS.md

## Design System

Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

Non-negotiable: every font in this app must ship a Greek `unicode-range`.
The UI renders Greek EUROVOC labels and Greek legislative text. DESIGN.md lists
the verified-good fonts and the ones that silently fail.
