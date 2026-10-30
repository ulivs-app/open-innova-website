"""Regression checks for chart data and measurements, with no network calls."""
import unittest
from unittest.mock import patch
import footprint as fp

class FootprintTests(unittest.TestCase):
    def test_model_units_and_water(self):
        # 1 GB: 0.300 kWh, 148.2 g CO2e, 0.055 kWh in operating data centres.
        report = fp.report_data([('/', 1_000_000_000, 500_000_000)], 'https://example.org', 'test', {})
        self.assertAlmostEqual(report['first']['wh'], 300)
        self.assertAlmostEqual(report['first']['g'], 148.2)
        self.assertAlmostEqual(report['water'][0]['ml_per_load'], 99)
        self.assertAlmostEqual(report['water'][1]['ml_per_load'], 2.75)
        self.assertAlmostEqual(sum(s['percent'] for s in report['segments']), 100)
        self.assertAlmostEqual(report['water'][0]['loads_per_500ml'] * 99, 500)

    def test_arithmetic_mean_not_sum(self):
        data = fp.report_data([('/', 10000, 5000), ('/about/', 30000, 9000)], 'https://example.org', 'release-a', {})
        self.assertEqual(data['first_bytes'], 20000)
        self.assertEqual(data['next_bytes'], 7000)
        self.assertEqual(data['heaviest_bytes'], 30000)
        self.assertEqual(data['page_count'], 2)
        self.assertEqual(data['version_label'], 'release-a')
        with self.assertRaises(ValueError):
            fp.report_data([], '', '', {})

    def test_assets_attribute_order_duplicates_and_external_urls(self):
        html = '''<link href='/a.css' rel='stylesheet'><script defer src='/a.js'></script>
          <link rel='stylesheet' href='/a.css'><img src='https://example.org.evil/a.png'>
          <link rel='alternate' href='/data.json'><img src='/a.png'>'''
        self.assertEqual(fp.subresources(html, 'https://example.org'),
                         ['https://example.org/a.css', 'https://example.org/a.js', 'https://example.org/a.png'])

    def test_no_store_resources_are_transferred_on_warm_load(self):
        html = '<script src="/a.js"></script><script src="/b.js"></script>'
        def measure(url):
            if url.endswith('/a.js'): return 1000, 100, 'no-store'
            if url.endswith('/b.js'): return 2000, 100, 'public, immutable'
            return 3000, 200, ''
        with patch('sys.argv', ['footprint.py', '--base-url', 'https://example.org']), \
             patch.object(fp, 'sitemap_pages', return_value=['https://example.org/']), \
             patch.object(fp, 'fetch_text', return_value=html), \
             patch.object(fp, 'measure', side_effect=measure), \
             patch.object(fp, 'report_data', wraps=fp.report_data) as report, \
             patch('builtins.print'):
            fp.main()
        self.assertEqual(report.call_args.args[0], [('/', 6400, 4300)])

if __name__ == '__main__':
    unittest.main()
