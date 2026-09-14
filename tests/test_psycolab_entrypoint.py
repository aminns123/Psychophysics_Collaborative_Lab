from psychophysics_lab.app import build_parser


def test_cli_parser_supports_noninteractive_checks():
    parser = build_parser()
    assert parser.parse_args(["--diagnose"]).diagnose is True
    assert parser.parse_args(["--list-experiments"]).list_experiments is True
