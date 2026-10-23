"""Slate Precision: researcher-facing Textual styling only.

The shared Option B router, stimulus rendering, run logic and calibration
requirements are deliberately outside this stylesheet.
"""

SLATE_PRECISION_CSS = """
/* Textual's application header/footer and modal behaviour stay unchanged. */
Screen.laboratory-console {
    background: #101923;
    color: #e2ebf3;
}
Screen.laboratory-console #console-heading {
    background: #182634;
    color: #f1f6fa;
    border-bottom: solid #3685a4;
}
Screen.laboratory-console #hub-nav {
    background: #172431;
    border-right: solid #344b5d;
}
Screen.laboratory-console #laboratory-label {
    color: #a9c1ce;
    text-style: bold;
}
Screen.laboratory-console #hub-nav Button {
    background: #172431;
    color: #d1dfeb;
}
Screen.laboratory-console #hub-nav Button.nav-selected {
    background: #246b8c;
    color: #ffffff;
    text-style: bold;
}
Screen.laboratory-console #hub-nav Button:focus {
    background: #35566b;
    color: #ffffff;
    text-style: bold underline;
}
Screen.laboratory-console #hub-nav Button:hover {
    background: #2b465b;
}
Screen.laboratory-console #hub-nav #refresh-psycolab {
    color: #aec1cb;
}
Screen.laboratory-console #fixed-shell {
    background: #14212e;
    border-bottom: solid #30495b;
}
Screen.laboratory-console Button {
    background: #273747;
    color: #e8f1f7;
    border: none;
}
Screen.laboratory-console Button:focus {
    text-style: bold underline;
    background: #365569;
}
Screen.laboratory-console Button.-primary {
    background: #236e90;
    color: #ffffff;
}
Screen.laboratory-console Button.-success {
    background: #276957;
    color: #ffffff;
}
Screen.laboratory-console Button.-warning {
    background: #96692e;
    color: #ffffff;
}
Screen.laboratory-console Button.-error {
    background: #8f4149;
    color: #ffffff;
}
Screen.laboratory-console Button:disabled {
    color: #9aa9b3;
}
Screen.laboratory-console #setup-body,
Screen.laboratory-console #review-body,
Screen.laboratory-console .page-body,
Screen.laboratory-console #config-body,
Screen.laboratory-console #code-body {
    background: #101923;
    border: none;
    padding: 1 2;
}
Screen.laboratory-console .info-card,
Screen.laboratory-console #experiment-inspection,
Screen.laboratory-console #experiment-description {
    background: #1b2937;
    border: solid #344b5d;
    padding: 1 2;
    margin-top: 1;
    margin-bottom: 1;
}
Screen.laboratory-console .field-help {
    color: #afc2cd;
}
Screen.laboratory-console .slate-section-title {
    background: #1b2b3b;
    color: #c3e6f4;
    border-left: heavy #3685a4;
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 1;
    height: auto;
    text-style: bold;
}
/* Never replace readiness colour semantics with a generic blue card. */
Screen.laboratory-console .readiness-blocked,
Screen.laboratory-console .readiness-next {
    border: solid #c2954d;
}
Screen.laboratory-console .readiness-next {
    border: heavy #c2954d;
}
Screen.laboratory-console .readiness-done {
    border: solid #5ca991;
}
Screen.laboratory-console .invalid-input {
    border: tall #c66b70;
}
/* Wide Setup: editable choices on the left; read-only context on the right. */
Screen.laboratory-console #setup-columns {
    width: 100%;
    height: 1fr;
    layout: horizontal;
}
Screen.laboratory-console #setup-columns #setup-body {
    width: 2fr;
    height: 100%;
    min-width: 0;
}
Screen.laboratory-console #setup-side {
    width: 1fr;
    min-width: 0;
    height: 100%;
    background: #162532;
    border-left: solid #344b5d;
    padding: 1;
}
Screen.laboratory-console #setup-side .info-card {
    padding: 1;
}
/* Preserve both forms and read-only context on compact terminals. */
Screen.console-compact #setup-columns {
    layout: vertical;
}
Screen.console-compact #setup-columns #setup-body {
    width: 100%;
    height: 2fr;
}
Screen.console-compact #setup-side {
    width: 100%;
    height: 1fr;
    min-height: 3;
    border-left: none;
    border-top: solid #344b5d;
    padding: 0 1;
}
Screen.console-compact .slate-section-title {
    padding: 0 1;
}
/* Keep the fixed top action bar accessible on small displays. */
Screen.console-compact #fixed-shell {
    max-height: 45%;
}
"""
