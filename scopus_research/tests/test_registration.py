import sys
import unittest
from pathlib import Path

PLUGIN_PARENT = Path(__file__).resolve().parents[2]
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))

import scopus_research


class FakeContext:
    def __init__(self):
        self.tools = []
        self.skills = []

    def register_tool(self, **kwargs):
        self.tools.append((kwargs["name"], kwargs["toolset"]))

    def register_skill(self, *args):
        self.skills.append(args)


class RegistrationTests(unittest.TestCase):
    def test_all_research_tools_register(self):
        ctx = FakeContext()
        scopus_research.register(ctx)
        names = {name for name, _ in ctx.tools}
        self.assertEqual(len(ctx.tools), 6)
        self.assertTrue({
            "arxiv_search", "semantic_scholar_search", "scopus_search",
            "scopus_abstract", "scopus_author_search", "google_scholar_search",
        }.issubset(names))
        self.assertEqual(len(ctx.skills), 1)


if __name__ == "__main__":
    unittest.main()
