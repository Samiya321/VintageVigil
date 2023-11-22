import asyncio
import httpx
import re
import json
from loguru import logger
from typing import AsyncGenerator, List, Optional
from .search_result_item import SearchResultItem