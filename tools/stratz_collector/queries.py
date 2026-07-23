"""GraphQL operations used by the existing D2Helper browser collector."""

from __future__ import annotations


STATS_QUERY = """
{
  heroStats {
    stats {
      week
    }
  }
}
"""


MATCHUP_QUERY = """
query LoadWeek($week: Long!) {
  heroStats {
    matchUp(
      take: 200
      week: $week
    ) {
      heroId
      with {
        heroId1
        heroId2
        synergy
        matchCount
      }
      vs {
        heroId1
        heroId2
        synergy
        matchCount
      }
    }
  }
}
"""
