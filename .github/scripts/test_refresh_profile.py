import unittest

from refresh_profile import contribution_table, language_chart, update_front


class ProfileRefreshTests(unittest.TestCase):
    def test_chart_keeps_native_block_bars_and_percentages(self):
        chart = language_chart(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text data-testid="lang-name">\nPython 57.84%\n</text>'
            '<text data-testid="lang-name">Nix 13.89%</text></svg>'
        )
        self.assertIn("57.84 %", chart)
        self.assertEqual(chart.splitlines()[0].count("▓"), 10)
        for line in chart.splitlines():
            self.assertEqual(line.count("▓") + line.count("░"), 17)

    def test_error_cards_and_malformed_statistics_fail(self):
        for malformed in [
            "missing",
            '<svg xmlns="http://www.w3.org/2000/svg"><text>Something went wrong</text></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><text data-testid="lang-name">Python 101%</text></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><text data-testid="lang-name">Python</text></svg>',
        ]:
            with self.subTest(statistics=malformed), self.assertRaises(ValueError):
                language_chart(malformed)

    def test_upstream_percentages_and_language_names_are_preserved(self):
        chart = language_chart(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text data-testid="lang-name">C&amp;C++ 0.01%</text>'
            '<text data-testid="lang-name">Jupyter Notebook 99.98%</text></svg>'
        )
        self.assertIn("C&amp;C++", chart)
        self.assertIn("Jupyter Notebook", chart)
        self.assertIn("0.01 %", chart)
        self.assertIn("99.98 %", chart)

    def test_contribution_titles_preserve_the_markdown_table(self):
        table = contribution_table(
            [
                {
                    "repo": "owner/project",
                    "repo_url": "https://github.com/owner/project",
                    "prs": [
                        {
                            "number": 1,
                            "url": "https://github.com/owner/project/pull/1",
                            "title": "fix: A | B\n<script>",
                        }
                    ],
                }
            ]
        )
        self.assertEqual(len(table.splitlines()), 3)
        self.assertIn(r"A \| B &lt;script&gt;", table)
        self.assertEqual(len(contribution_table([]).splitlines()), 2)

    def test_refresh_updates_only_generated_sections(self):
        original = "before<pre>old</pre>between<!-- OSS_CONTRIBUTIONS:START -->old<!-- OSS_CONTRIBUTIONS:END -->after"
        statistics = '<svg xmlns="http://www.w3.org/2000/svg"><text data-testid="lang-name">Python 100.00%</text></svg>'
        updated = update_front(original, statistics, [])
        self.assertTrue(updated.startswith("before<pre>"))
        self.assertTrue(updated.endswith("<!-- OSS_CONTRIBUTIONS:END -->after"))
        self.assertIn("</pre>between<!-- OSS_CONTRIBUTIONS:START -->", updated)
        self.assertNotIn("old", updated)
        for invalid in ["no blocks", "<pre>chart</pre>"]:
            with self.subTest(markdown=invalid), self.assertRaises(ValueError):
                update_front(invalid, statistics, [])


if __name__ == "__main__":
    unittest.main()
