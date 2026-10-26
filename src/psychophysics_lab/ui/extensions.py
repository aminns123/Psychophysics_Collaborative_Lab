"""Minimal trusted-root controls inside the existing experiment catalogue."""
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Button, Checkbox, Static
from .checkbox import ExplicitCheckbox as Checkbox
from .. import extensions
from ..config.local import preferences


class ExtensionsPanel(Vertical):
    def compose(self):
        setting = preferences(self.app.local_config_root).get('extensions', {})
        if not isinstance(setting, dict):
            setting = {}
        yield Static('LABORATORY EXTENSIONS', classes='section-title')
        yield Static('A starter folder is prepared beside PsyCoLab on first launch. You can change its location at any time; existing files are never overwritten.')
        yield Static('External Python runs with your machine permissions; this is not a sandbox. Software Ready does not qualify a display.')
        yield Input(value=setting.get('root') or str(extensions.suggested_root(self.app.repo_root)),
                    placeholder='Absolute extensions folder', id='extensions-root')
        yield Checkbox('I trust the Python code in this folder', id='extensions-trust')
        with Horizontal(classes='buttons'):
            yield Button('Create starter at this location', id='extensions-starter')
            yield Button('Enable trusted folder', id='extensions-enable')
            yield Button('Disable extensions', id='extensions-disable')
        yield Static('', id='extensions-status', markup=False)

    def on_mount(self):
        self.refresh_status()

    def refresh_status(self):
        try:
            current = extensions.configured(self.app.repo_root, self.app.data_root)
            message = 'Disabled; built-in experiments remain available.' if current is None else 'Enabled: ' + current[1]
            if current:
                message += '\n' + '\n'.join(f"{row['kind']} {row['id']}: {row['status']}" for row in extensions.inventory(self.app.repo_root))
            if extensions._errors:
                message += '\n' + '\n'.join(f'{key}: {value}' for key,value in extensions._errors.items())
        except (ValueError, OSError) as exc:
            message = str(exc)
        self.query_one('#extensions-status', Static).update(message)

    def on_button_pressed(self, event):
        if event.button.id not in {'extensions-enable', 'extensions-disable', 'extensions-starter'}:
            return
        event.stop()
        try:
            location = self.query_one('#extensions-root', Input).value
            if event.button.id == 'extensions-starter':
                path, created = extensions.initialise_starter(
                    self.app.repo_root, location, data_root=self.app.data_root
                )
                self.query_one('#extensions-status', Static).update(
                    ('Starter files created at: ' if created else 'Existing extension files preserved at: ')
                    + str(path) + '\nPython is NOT trusted/enabled yet; review it, '
                    'then tick the trust checkbox and enable.'
                )
                return
            extensions.configure(self.app.repo_root,
                location if event.button.id == 'extensions-enable' else None,
                trusted=self.query_one('#extensions-trust', Checkbox).value, data_root=self.app.data_root)
            self.query_one('#extensions-status', Static).update('Saved. Use Refresh (F5) or restart to rebuild the catalogue. Existing extension selections cannot run after disabling.')
        except (ValueError, OSError) as exc:
            self.query_one('#extensions-status', Static).update(str(exc))
