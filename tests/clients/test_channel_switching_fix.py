"""Test for the fix to ensure cache is only cleared when channel actually changes."""

import unittest

# No specific imports needed here

# Import the ElasticsearchClient class that we fixed
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient


class TestChannelSwitchingFix(unittest.TestCase):
    """Test the fix for channel switching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a client for testing
        self.client = ElasticsearchClient()

        # Track cache clearing
        self.original_clear = self.client.cache.clear
        self.cache_clear_count = 0

        def mock_clear():
            self.cache_clear_count += 1
            return self.original_clear()

        self.client.cache.clear = mock_clear

    def tearDown(self):
        """Tear down test fixtures."""
        if hasattr(self, "client") and hasattr(self.client, "cache"):
            self.client.cache.clear = self.original_clear

    def test_cache_cleared_only_on_actual_change(self):
        """Test that cache is only cleared when channel actually changes."""
        # Reset counter
        self.cache_clear_count = 0

        # First set channel to current value (unstable) - should not clear cache
        current_channel = self.client._current_channel_id
        current_channel_name = next(
            name for name, cid in self.client.available_channels.items() if cid == current_channel
        )

        # Call set_channel with same channel multiple times
        self.client.set_channel(current_channel_name)
        self.client.set_channel(current_channel_name)
        self.client.set_channel(current_channel_name)

        # Cache should not be cleared if channel didn't change
        self.assertEqual(self.cache_clear_count, 0, "Cache was cleared despite channel not changing")

        # Now set to a different channel - should clear cache
        different_channel = "24.11" if current_channel_name != "24.11" else "unstable"
        self.client.set_channel(different_channel)

        # Verify cache was cleared exactly once
        self.assertEqual(self.cache_clear_count, 1, "Cache should be cleared exactly once when changing channel")

        # Try setting to the same new channel multiple times - should not clear again
        self.client.set_channel(different_channel)
        self.client.set_channel(different_channel)

        # Cache should still only be cleared once
        self.assertEqual(self.cache_clear_count, 1, "Cache was incorrectly cleared when setting to same channel")

    def test_urls_always_updated(self):
        """Test that URLs are always updated regardless of channel changes."""
        # Get initial URLs
        initial_packages_url = self.client.es_packages_url
        initial_options_url = self.client.es_options_url

        # Call set_channel with current channel
        current_channel = self.client._current_channel_id
        current_channel_name = next(
            name for name, cid in self.client.available_channels.items() if cid == current_channel
        )
        self.client.set_channel(current_channel_name)

        # URLs should be set even if channel didn't change
        self.assertEqual(initial_packages_url, self.client.es_packages_url)
        self.assertEqual(initial_options_url, self.client.es_options_url)

        # Now change to different channel
        different_channel = "24.11" if current_channel_name != "24.11" else "unstable"
        self.client.set_channel(different_channel)

        # URLs should be different
        self.assertNotEqual(initial_packages_url, self.client.es_packages_url)
        self.assertNotEqual(initial_options_url, self.client.es_options_url)

    def test_channel_state_always_updated(self):
        """Test that internal channel state is always updated."""
        # Get current channel
        original_channel_id = self.client._current_channel_id

        # Set to different channel
        different_channel = "24.11" if "unstable" in original_channel_id else "unstable"
        self.client.set_channel(different_channel)

        # Internal state should be updated
        different_channel_id = self.client.available_channels[different_channel]
        self.assertEqual(self.client._current_channel_id, different_channel_id)
        self.assertNotEqual(original_channel_id, self.client._current_channel_id)

    def test_25_05_beta_channel_support(self):
        """Test support for the NixOS 25.05 Beta channel."""
        # Reset counter
        self.cache_clear_count = 0

        # Verify 25.05 is in available channels
        self.assertIn("25.05", self.client.available_channels, "25.05 channel not found in available channels")

        # Get index ID for 25.05 channel
        beta_channel_id = self.client.available_channels["25.05"]
        self.assertTrue(beta_channel_id.endswith("-25.05"), "25.05 channel ID doesn't have proper suffix")

        # Set channel to 25.05 and verify it updates correctly
        self.client.set_channel("25.05")
        self.assertEqual(self.client._current_channel_id, beta_channel_id, "Failed to set channel to 25.05")
        self.assertEqual(self.cache_clear_count, 1, "Cache should be cleared when switching to 25.05")

        # URLs should be updated with the correct index
        self.assertIn(beta_channel_id, self.client.es_packages_url, "URL not updated with 25.05 index")
        self.assertIn(beta_channel_id, self.client.es_options_url, "URL not updated with 25.05 index")

        # Switching between multiple channels should work correctly
        # 25.05 -> unstable
        self.client.set_channel("unstable")
        self.assertEqual(self.cache_clear_count, 2, "Cache should be cleared when switching from 25.05 to unstable")

        # unstable -> 24.11
        self.client.set_channel("24.11")
        self.assertEqual(self.cache_clear_count, 3, "Cache should be cleared when switching to 24.11")

        # 24.11 -> 25.05
        self.client.set_channel("25.05")
        self.assertEqual(self.cache_clear_count, 4, "Cache should be cleared when switching back to 25.05")

        # 25.05 -> stable (which is 24.11)
        self.client.set_channel("stable")
        self.assertEqual(self.cache_clear_count, 5, "Cache should be cleared when switching from 25.05 to stable")

        # Get current channel name after setting to "stable"
        stable_channel_id = self.client._current_channel_id
        stable_channel_name = next(
            name
            for name, cid in self.client.available_channels.items()
            if cid == stable_channel_id and name != "stable"
        )
        self.assertEqual(stable_channel_name, "24.11", "Stable channel should map to 24.11")

    def test_stable_channel_alias_preserved(self):
        """Test that the stable channel alias is still mapped to 24.11 after adding 25.05."""
        # Verify stable still maps to 24.11
        self.assertEqual(
            self.client.available_channels["stable"],
            self.client.available_channels["24.11"],
            "Stable channel should still map to 24.11",
        )

        # Set channel to stable
        self.client.set_channel("stable")

        # Get the elasticsearch index ID that was actually used
        current_index = self.client._current_channel_id

        # Verify it's the same as 24.11
        self.assertEqual(
            current_index, self.client.available_channels["24.11"], "Stable should resolve to the same index as 24.11"
        )

    def test_beta_channel_alias(self):
        """Test that the beta channel alias is correctly mapped to 25.05."""
        # Verify beta maps to 25.05
        self.assertEqual(
            self.client.available_channels["beta"],
            self.client.available_channels["25.05"],
            "Beta channel should map to 25.05",
        )

        # Reset counter
        self.cache_clear_count = 0

        # Set channel to beta
        self.client.set_channel("beta")

        # Get the elasticsearch index ID that was actually used
        current_index = self.client._current_channel_id

        # Verify it's the same as 25.05
        self.assertEqual(
            current_index, self.client.available_channels["25.05"], "Beta should resolve to the same index as 25.05"
        )

        # Get the current cache_clear_count to avoid depending on previous state
        current_count = self.cache_clear_count

        # Set to a different channel and then back to beta to verify cache clearing
        self.client.set_channel("unstable")
        self.assertEqual(
            self.cache_clear_count, current_count + 1, "Cache should be cleared when switching from beta to unstable"
        )

        self.client.set_channel("beta")
        self.assertEqual(
            self.cache_clear_count, current_count + 2, "Cache should be cleared when switching back to beta"
        )


if __name__ == "__main__":
    unittest.main()
