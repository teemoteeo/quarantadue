*This project has been created as part of the 42 curriculum by tcostant*

## PUSH_SWAP

## Description

Sort integers across two stacks using limited operations. This implementation uses the **Turkish Algorithm** with cost-based optimization.

## Algorithm

# -UTILS:

   Manipulation functions(swap, push, rotate)
    **->swap**: swaps the first and second element of given stack.
    **->push**: takes first element of a stack and puts it on top of another one.
    **->rotate**: takes first element of stack and puts it at the bottom.
    **->rev rotate**: takes last element of stack and puts it ath the top.

   Indexing(assign_index, get_min_index_position)
    **Work with indexes not values**: set up stacks to operate on relative relationships and not absolute values;

   Cost analysis(find_cheapest)
    **Optimize for operational cost**: target elements which take the less operation to be on top of the B stack +
                                       less operation to bring target_index at stack A top.

# -CODEFLOW:

1. **index normalization**: convert values to ranks 0 to n-1
2. **push to B**: move all elements except 3 to stack B
3. **sort 3 in A**: hardcoded general moves, for 3, 4 and 5 elements
4. **push back**: for each element in B, calculate the cheapest move and push to correct position in A
5. **final rotate**: rotate A so minimum is on top

```
Phase 1: Push all to B (keep 3 in A)
Phase 2: Sort the 3 remaining
Phase 3: For each in B:
    - Find target position in A
    - Calculate cost (use rr/rrr when possible)
    - Execute cheapest move
    - pa
Phase 4: Rotate A to put min on top
```

## Build & Run

```bash
make
./push_swap 3 2 1 0
```

Test:
```bash
ARG="$(shuf -i 1-1000 -n 100)"; ./a.out $ARG | wc -l
```

## Resources

- Turkish Algorithm explanation
- Cost-based sorting optimization
- Stack data structures
- AI: Chatgpt for brainstorming, Claude for coding assistance
