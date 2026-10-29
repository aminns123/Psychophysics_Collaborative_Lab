try:
    from .app import main
except Exception as error:
    # Imports can fail before app.main installs its normal diagnostic boundary.
    from .diagnostics import notify_launcher_exit, write_crash_report
    from .paths import find_repo_root
    try:
        root = find_repo_root()
    except Exception:
        root = None
    report = write_crash_report(error, repo_root=root, phase="application_startup")
    notify_launcher_exit("application_startup", report)
    raise

if __name__ == "__main__":
    raise SystemExit(main())
