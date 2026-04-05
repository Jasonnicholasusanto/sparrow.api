# For database representation (SQLModel)
# --------------------------------------------------------------------------------------------------------------
# What it is: A representation of a table in the database — usually tied to ORM (Object-Relational Mapping).
# Purpose: Used to read/write data from the DB.
# Significance: Bridges Python objects with database rows.
# Knows about database fields, constraints, and sometimes relationships (foreign keys, etc.).

from .auth import User
from .user_profile import UserProfile
from .user_activity import UserActivity
from .user_follow import UserFollow
from .navbar_routes import NavbarRoute
from .point_rule import PointRule
from .watchlist import Watchlist
from .watchlist_bookmark import WatchlistBookmark
from .watchlist_item import WatchlistItem
from .watchlist_share import WatchlistShare
from .vote import Vote
from .search_history import SearchHistory

__all__ = [
    "User",
    "UserProfile",
    "UserActivity",
    "UserFollow",
    "NavbarRoute",
    "PointRule",
    "Watchlist",
    "WatchlistBookmark",
    "WatchlistItem",
    "WatchlistShare",
    "Vote",
    "SearchHistory",
]
