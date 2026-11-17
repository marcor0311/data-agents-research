"""Meaningful validation edge cases; run with unittest discovery."""
import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prepare_dataset', Path(__file__).with_name('prepare_dataset.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    path = module.ROOT.parent / 'Anime-dataset/data/raw/anime_seasonal_20261116.csv'
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return next(csv.DictReader(stream))


class PreparationTests(unittest.TestCase):
    def test_partial_dates_keep_precision(self):
        for value, precision, last in [('2020', 'year', date(2020, 12, 31)),
                                       ('2020-02', 'month', date(2020, 2, 29))]:
            parsed = module.parse_date(value)
            self.assertEqual(parsed[0], value)
            self.assertEqual(parsed[1], precision)
            self.assertEqual(parsed[3], last)
        with self.assertRaises(ValueError):
            module.parse_date('2020-02-30')

    def test_zero_policies_preserve_votes_and_originals(self):
        row = sample()
        row.update(score='0.0', scored_by='20', episodes='0', rank='0')
        normalized = module.normalize(row, date(2026, 11, 16))
        self.assertIsNone(normalized['score'])
        self.assertIsNone(normalized['episodes'])
        self.assertIsNone(normalized['rank'])
        self.assertEqual(normalized['scored_by'], 20)
        self.assertEqual(normalized['source_values']['score'], '0.0')
        self.assertTrue(all(normalized[key] is None for key in module.UNAVAILABLE))

    def test_invalid_score_and_changed_statistics_rejected(self):
        row = sample()
        row['score'] = '10.5'
        with self.assertRaises(ValueError):
            module.normalize(row, date(2026, 11, 16))
        row = sample()
        row['members'] = '1'
        with self.assertRaises(ValueError):
            module.normalize(row, date(2026, 11, 16))

    def test_future_dates_can_be_uncertain(self):
        row = sample()
        row['start_date'] = '2026-11'
        normalized = module.normalize(row, date(2026, 11, 16))
        self.assertIsNone(normalized['future_start'])
        row['start_date'] = '2026-12'
        self.assertTrue(module.normalize(row, date(2026, 11, 16))['future_start'])

    def test_invalid_input_does_not_replace_current_pointer(self):
        with tempfile.TemporaryDirectory(prefix='anime-preparation-test-') as folder:
            root = Path(folder)
            source = root / 'invalid.csv'
            row = sample()
            row['anime_id'] = '0'
            with source.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=module.FIELDS)
                writer.writeheader()
                writer.writerow(row)
            output = root / 'processed'
            output.mkdir()
            pointer = output / 'current.json'
            pointer.write_text('{"previous":true}', encoding='utf-8')
            before = pointer.read_bytes()
            with patch.object(module.subprocess, 'check_output') as git:
                with self.assertRaises(ValueError):
                    module.build(source, output, root, date(2026, 11, 16))
                git.assert_not_called()
            self.assertEqual(pointer.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
