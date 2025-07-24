# Proposal 001: Add Pytest Testing Framework

## Description
Add pytest as a dev dependency and create initial test suite for core market mechanics.

## Rationale
- Current test coverage: 0%
- Testing will improve code quality score significantly
- Catch bugs before they affect market operations
- Enable confident refactoring

## Implementation
1. Add pytest to pyproject.toml dev dependencies
2. Create tests/ directory structure
3. Write tests for:
   - Market.buy_shares() mechanics
   - AMM price calculations
   - User balance updates
   - Database operations

## Success Metrics
- Test coverage > 60% within 1 week
- All tests passing in CI
- Code quality score increases by 15+ points

## Risks
- Initial time investment (~4 hours)
- May discover existing bugs requiring fixes
- Could slow down development velocity temporarily

## Rollback Plan
- Simply remove pytest if it proves problematic
- No changes to production code required