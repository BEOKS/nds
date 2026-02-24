# Code Review Rules

## 1. Review Mindset

Goals: catch bugs/edge cases, ensure maintainability, share knowledge, enforce standards, improve design.
Not goals: show off, nitpick formatting, block progress, rewrite to preference.

## 2. Effective Feedback

- Specific and actionable
- Educational, not judgmental
- Focused on code, not the person
- Balanced (praise good work too)
- Prioritized (critical vs nice-to-have)

Bad: "This is wrong."
Good: "This could cause a race condition when multiple users access simultaneously. Consider using a mutex here."

Bad: "Why didn't you use X pattern?"
Good: "Have you considered the Repository pattern? It would make this easier to test."

## 3. Review Phases

### Phase 1: Context Gathering (2-3 min)
1. Read MR description and linked issue
2. Check MR size (>400 lines? suggest split)
3. Understand the business requirement

### Phase 2: High-Level Review (5-10 min)
- Architecture & Design: Does the solution fit? Simpler approaches? Consistent patterns? Scalable?
- File Organization: Right places? Logical grouping? Duplicates?
- Testing Strategy: Tests exist? Edge cases? Readable?

### Phase 3: Line-by-Line Review (10-20 min)
- **Logic & Correctness**: Edge cases, off-by-one, null checks, race conditions
- **Security**: Input validation, SQL injection, XSS, sensitive data exposure
- **Performance**: N+1 queries, unnecessary loops, memory leaks, blocking ops
- **Maintainability**: Clear names, single-responsibility functions, comments for complexity

### Phase 4: Summary & Decision (2-3 min)
Summarize concerns, highlight positives, make decision.

## 4. Severity Labels

- P1 [blocking]: Must fix before merge (bugs, security, data integrity)
- P2 [important]: Should fix (architecture, performance, maintainability)
- P3 [minor]: Nice to have (style, naming, simple refactoring)
- P4 [suggestion]: Alternative approach, opinion
- P5 [praise]: Good code, thorough handling

## 5. Feedback Technique

Use questions over commands:
- "What happens if `items` is an empty array?"
- "How should this behave if the API call fails?"
- "Have we considered the performance impact with 100k users?"

Use collaborative language:
- "Suggestion: async/await might make this more readable. What do you think?"
- "This logic appears in 3 places. Would it make sense to extract it?"

## 6. Language-Specific Checks

### Python
- Mutable default arguments (`def f(items=[])` bug)
- Broad exception catching (`except:` vs `except ValueError`)
- Mutable class attributes shared across instances

### TypeScript/JavaScript
- `any` type defeating type safety
- Unhandled async errors
- Prop mutation in React components
- Missing error boundaries

### General
- SQL queries parameterized?
- Passwords hashed (bcrypt/argon2)?
- Secrets not hardcoded?
- CSRF/XSS protection?
- Rate limiting on public endpoints?

## 7. Test Quality

- Tests describe behavior, not implementation
- Test names are clear and descriptive
- Edge cases covered
- Tests are independent (no shared state)
- Tests are deterministic

## 8. Output Format

```
## Code Review: <MR Title>

**MR**: <url>
**Author**: <author>
**Branch**: <source> -> <target>

---

### P1: Critical (Must Fix)
- **[file:line]** description
  - Problem: ...
  - Suggestion: ...

### P2: Major (Strongly Recommended)
- **[file:line]** description

### P3: Minor (Preferred)
- **[file:line]** description

### P4: Suggestion/Opinion
- **[file:line]** description

### P5: Praise
- **[file:line]** description
```
