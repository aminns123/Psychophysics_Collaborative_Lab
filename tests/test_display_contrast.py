import json
from pathlib import Path
import tempfile
import unittest

from Events.display_contrast import normalized_display_contrast, display_contrast_to_screen_intensity
from Events.adaptiveMethods import (
    _to_weber, convert_screen_intensity_history_to_weber_contrast_list,
    convert_weber_contrast_to_screenIntensity,
)
from Interface.config import run_configure_experiment


class DisplayContrastTests(unittest.TestCase):
    def test_background_and_maximum_endpoints(self):
        self.assertEqual(normalized_display_contrast(.24, background_intensity=.24, maximum_intensity=1), 0)
        self.assertEqual(normalized_display_contrast(1, background_intensity=.24, maximum_intensity=1), 1)

    def test_not_conventional_weber(self):
        actual = normalized_display_contrast(.5, background_intensity=.25, maximum_intensity=1)
        self.assertAlmostEqual(actual, 1 / 3)
        self.assertNotEqual(actual, (.5 - .25) / .25)

    def test_round_trip_and_legacy_compatibility(self):
        for background in [0., .24, .8, .99]:
            for contrast in [0., .01, .25, 1., 1.2]:
                with self.subTest(background=background, contrast=contrast):
                    intensity = display_contrast_to_screen_intensity(contrast,
                        background_intensity=background, maximum_intensity=1.)
                    self.assertAlmostEqual(normalized_display_contrast(intensity,
                        background_intensity=background, maximum_intensity=1.), contrast)
                    self.assertEqual(_to_weber(intensity, background, 1.),
                                     convert_screen_intensity_history_to_weber_contrast_list([intensity], background, 1.)[0])
                    self.assertEqual(convert_weber_contrast_to_screenIntensity(1., background, contrast), intensity)

    def test_no_implicit_clipping(self):
        self.assertEqual(normalized_display_contrast(1.5, background_intensity=.5, maximum_intensity=1), 2)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            normalized_display_contrast(.5, background_intensity=1, maximum_intensity=1)

    def test_log_option_preserved(self):
        self.assertAlmostEqual(convert_screen_intensity_history_to_weber_contrast_list(
            [.325], .25, 1, apply_log=True)[0], -1)

    def test_configuration_arguments_fixed_without_changing_defaults_or_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            participant = Path(folder) / 'test'
            participant.mkdir()
            setup = {
                'Background_Screen_intensity': .24, 'Max_monitor_Luminance': 500,
                'starting_probe_intensity': 1., 'reversal_termination': 10,
                'trialPOINT': 9, 'Experiment_Type': 'contrast_sensitivity_function',
            }
            (participant / 'experiment_defined.json').write_text(json.dumps(setup))
            conditions, parameters, _ = run_configure_experiment('test', folder, setup)
            state = json.loads(Path(conditions).read_text())
            params = json.loads(Path(parameters).read_text())
            self.assertEqual(state['starting_contrast'], [1., 1.])
            self.assertEqual(state['weber_contrast_active'], [1., 1.])
            self.assertEqual(params['background_weber_contrast'], 0.)
            self.assertEqual(params['max_weber_contrast'], 1.)
            self.assertNotIn('background_display_contrast', params)
            self.assertEqual((params['n_dw'], params['n_up']), (2, 1))
            self.assertEqual((params['logUNIT_UP'], params['logUNIT_DW']), (.35, .5488 * .35))
            self.assertEqual((params['timeFixate'], params['timeInterval'], params['timeAB'], params['timeT']), (250, 250, 200, 0))
            self.assertEqual(state['reversal_termination'], [10, 10])
            self.assertEqual(state['condition_list'], [63., 252.])
            global_config = json.loads((Path(folder) / 'user_experiment_config.json').read_text())
            self.assertEqual(global_config['experiment_params']['number_trials'], 30)


if __name__ == '__main__':
    unittest.main()
