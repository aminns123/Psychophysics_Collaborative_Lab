"""Coffee / forest visual refinements for the researcher console only.

No rules in this module affect the fullscreen participant stimulus renderer.
"""

COFFEE_FOREST_CSS = """
Screen.laboratory-console { background: #171914; color: #eee9de; }
Screen.laboratory-console #console-heading {
    background: #29261f; color: #f1ebdf;
    border-bottom: solid #58745b;
}
Screen.laboratory-console #hub-nav {
    background: #24271f; border-right: solid #547057;
}
Screen.laboratory-console #laboratory-label { color: #c9d0bf; }
Screen.laboratory-console #hub-nav Button {
    background: #24271f; color: #e7e3d6;
}
Screen.laboratory-console #hub-nav Button.nav-selected {
    background: #416b4d; color: #ffffff;
}
Screen.laboratory-console #hub-nav Button:focus {
    background: #55785b; color: #ffffff; text-style: bold underline;
}
Screen.laboratory-console #hub-nav Button:hover { background: #3a4939; }
Screen.laboratory-console #hub-nav #refresh-psycolab { color: #c8c5b7; }
Screen.laboratory-console #fixed-shell {
    background: #29261f; border-bottom: solid #51634e;
    height: auto; min-height: 0;
}
Screen.laboratory-console Button {
    background: #40352c; color: #f1e8d9; border: none;
}
Screen.laboratory-console Button:focus {
    background: #536448; color: #ffffff; text-style: bold underline;
}
Screen.laboratory-console Button.-primary {
    background: #416d4e; color: #ffffff;
}
Screen.laboratory-console Button.-success {
    background: #356f4c; color: #ffffff;
}
Screen.laboratory-console Button.-warning {
    background: #946326; color: #ffffff;
}
Screen.laboratory-console Button.-error {
    background: #8c3d44; color: #ffffff;
}
Screen.laboratory-console Button:disabled { color: #afa696; }
Screen.laboratory-console #setup-body,
Screen.laboratory-console #review-body,
Screen.laboratory-console .page-body,
Screen.laboratory-console #config-body,
Screen.laboratory-console #code-body {
    background: #171914; padding: 1 4 1 2; border: none;
}
Screen.laboratory-console #setup-side {
    background: #25281f; border-left: solid #547057;
    padding: 1 3 1 2;
}
Screen.laboratory-console .info-card,
Screen.laboratory-console #experiment-inspection,
Screen.laboratory-console #experiment-description {
    background: #292b25; border: solid #635546;
    padding: 1 2; margin-top: 1; margin-bottom: 1;
}
Screen.laboratory-console .field-help { color: #c1bbab; }
Screen.laboratory-console .slate-section-title,
Screen.laboratory-console .section-title {
    color: #dbe4cd; background: #30372b;
    border-left: heavy #668263; padding: 0 1;
    height: auto; text-style: bold; margin-top: 1; margin-bottom: 1;
}
/* Calibration readiness states retain independent amber/green/red meaning. */
Screen.laboratory-console .readiness-blocked,
Screen.laboratory-console .readiness-next { border: solid #bc954e; }
Screen.laboratory-console .readiness-next { border: heavy #bc954e; }
Screen.laboratory-console .readiness-done { border: solid #5ba17b; }
Screen.laboratory-console .readiness-optional { border: solid #635546; }
Screen.laboratory-console .invalid-input { border: tall #bd6467; }
/* Stable maximum control width; forms still shrink at compact widths. */
Screen.laboratory-console #setup-body Input,
Screen.laboratory-console #setup-body Select,
Screen.laboratory-console #review-body Input,
Screen.laboratory-console #review-body Select,
Screen.laboratory-console #config-body Input,
Screen.laboratory-console #config-body Select,
Screen.laboratory-console .page-body Input,
Screen.laboratory-console .page-body Select {
    width: 100%; max-width: 76;
}
Screen.laboratory-console .page-body .buttons,
Screen.laboratory-console #review-body .buttons,
Screen.laboratory-console #config-body .buttons {
    layout: vertical; height: auto; align-horizontal: left;
}
Screen.laboratory-console .page-body .buttons Button,
Screen.laboratory-console #review-body .buttons Button,
Screen.laboratory-console #config-body .buttons Button {
    width: 38; min-width: 0; max-width: 100%;
    height: 3; margin: 0 0 1 0;
}
Screen.laboratory-console .page-body > Button,
Screen.laboratory-console #setup-body > Button,
Screen.laboratory-console #review-body > Button,
Screen.laboratory-console #config-body > Button {
    width: 38; min-width: 0; max-width: 100%;
    height: 3; margin: 0 0 1 0;
}
/* Header actions remain stationary above page scroll panes. */
Screen.laboratory-console #fixed-shell .buttons Button {
    width: 1fr; max-width: 32; min-width: 0;
}
Screen.laboratory-console #setup-status,
Screen.laboratory-console #review-status,
Screen.laboratory-console #config-status,
Screen.laboratory-console #data-status {
    margin-top: 0; min-height: 0;
}
/* A clear margin before scrollbar rails. */
Screen.laboratory-console #calibration-pages .calibration-panel {
    padding-right: 4;
}
/* Scientific review matrix remains intact and horizontally inspectable. */
Screen.laboratory-console #resolved-settings-table {
    width: 100%; max-width: 100%;
}
Screen.console-compact #setup-side {
    border-left: none; border-top: solid #547057; padding: 1 2;
}
Screen.console-compact .page-body .buttons,
Screen.console-compact #review-body .buttons,
Screen.console-compact #config-body .buttons {
    layout: vertical; height: auto;
}
Screen.console-compact .page-body .buttons Button,
Screen.console-compact #review-body .buttons Button,
Screen.console-compact #config-body .buttons Button {
    width: 100%; max-width: 100%;
}
"""
