"""
Synonym Dictionary for SQL Question Augmentation
"""

import random

# =============================================================================
# SYNONYMS BY CATEGORY
# =============================================================================

# Action Verbs
QUERY_VERBS = {
    "find": ["get", "show", "display", "list", "retrieve", "fetch", "return", "select"],
    "show": ["display", "list", "get", "find", "retrieve", "present"],
    "get": ["find", "show", "display", "list", "retrieve", "fetch", "obtain"],
    "list": ["show", "display", "get", "find", "enumerate"],
    "retrieve": ["get", "fetch", "find", "obtain", "extract"],
    "select": ["choose", "pick", "get", "retrieve", "find"],
    "search": ["find", "look for", "look up", "query"],
}

CALCULATION_VERBS = {
    "calculate": ["compute", "determine", "find", "figure out", "work out"],
    "compute": ["calculate", "determine", "figure out"],
    "count": ["tally", "enumerate", "number", "total up"],
    "sum": ["total", "add up", "aggregate"],
    "average": ["mean", "find the average of"],
}

MANIPULATION_VERBS = {
    "sort": ["order", "arrange", "rank", "organize"],
    "filter": ["narrow down", "limit", "restrict", "select"],
    "group": ["categorize", "organize", "cluster", "aggregate"],
    "join": ["combine", "merge", "connect", "link"],
    "update": ["modify", "change", "edit", "alter"],
    "delete": ["remove", "erase", "drop", "eliminate"],
    "insert": ["add", "create", "put", "include"],
}

# Comparison Terms
COMPARISONS = {
    "greater than": ["more than", "above", "exceeding", "over", "higher than"],
    "less than": ["below", "under", "fewer than", "smaller than", "lower than"],
    "equal to": ["equals", "is", "matching", "same as"],
    "between": ["in the range of", "ranging from", "within"],
    "contains": ["includes", "has", "with"],
}

# Aggregation Terms
AGGREGATIONS = {
    "maximum": ["highest", "largest", "greatest", "max", "top"],
    "minimum": ["lowest", "smallest", "least", "min", "bottom"],
    "average": ["mean", "avg"],
    "total": ["sum", "combined", "overall", "aggregate"],
    "count": ["number of", "how many", "total number of"],
    "distinct": ["unique", "different", "separate"],
}

# Business Entities
ENTITIES = {
    "employees": ["workers", "staff", "personnel", "team members"],
    "customers": ["clients", "users", "buyers", "patrons"],
    "products": ["items", "goods", "merchandise"],
    "orders": ["purchases", "transactions", "sales"],
    "suppliers": ["vendors", "providers", "distributors"],
    "company": ["firm", "organization", "business"],
    "department": ["dept", "division", "section", "unit"],
    "manager": ["supervisor", "boss", "lead", "head"],
}

# Financial Terms
FINANCIAL = {
    "price": ["cost", "amount", "value", "rate"],
    "salary": ["pay", "wage", "income", "earnings"],
    "revenue": ["income", "earnings", "sales"],
    "profit": ["earnings", "gain", "margin"],
    "cost": ["price", "expense", "charge"],
}

# Time Terms
TIME_TERMS = {
    "date": ["day", "time", "period"],
    "year": ["annum", "calendar year"],
    "month": ["period", "calendar month"],
    "recent": ["latest", "newest", "most recent"],
    "current": ["present", "existing", "active"],
    "previous": ["prior", "former", "past", "earlier"],
    "last": ["final", "most recent", "latest"],
    "first": ["initial", "earliest", "beginning"],
}

# Quantifiers
QUANTIFIERS = {
    "all": ["every", "each", "the entire", "complete"],
    "some": ["a few", "certain", "several"],
    "many": ["numerous", "multiple", "several"],
    "few": ["some", "a small number of", "limited"],
    "only": ["just", "solely", "exclusively"],
}

# Adjectives
ADJECTIVES = {
    "highest": ["greatest", "maximum", "largest", "top"],
    "lowest": ["smallest", "minimum", "least", "bottom"],
    "active": ["current", "live", "enabled"],
    "inactive": ["disabled", "dormant", "idle"],
    "new": ["recent", "latest", "fresh"],
    "old": ["previous", "former", "past"],
}

# =============================================================================
# COMBINED DICTIONARY
# =============================================================================

def get_all_synonyms():
    """Combine all synonym dictionaries."""
    all_synonyms = {}
    for d in [QUERY_VERBS, CALCULATION_VERBS, MANIPULATION_VERBS, 
              COMPARISONS, AGGREGATIONS, ENTITIES, FINANCIAL, 
              TIME_TERMS, QUANTIFIERS, ADJECTIVES]:
        all_synonyms.update(d)
    return all_synonyms

SYNONYMS = get_all_synonyms()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_synonym(word):
    """Get a random synonym for a word."""
    word_lower = word.lower()
    if word_lower in SYNONYMS:
        return random.choice(SYNONYMS[word_lower])
    return word

def has_synonym(word):
    """Check if a word has synonyms."""
    return word.lower() in SYNONYMS

def print_stats():
    """Print synonym statistics."""
    total_words = len(SYNONYMS)
    total_synonyms = sum(len(v) for v in SYNONYMS.values())
    print(f"Total words: {total_words}")
    print(f"Total synonyms: {total_synonyms}")

if __name__ == "__main__":
    print_stats()