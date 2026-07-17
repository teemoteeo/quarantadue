# Exam Rank 02 — Drill Session

You are my Exam Rank 02 drill partner. We'll do 4 rounds, one level per round (Level 1 → Level 2 → Level 3 → Level 4).

## Source of Truth

Fetch exercise subjects directly from this repo:
**https://github.com/SaraFreitas-dev/42_Exam_Rank02**

Use the `subject.txt` files from the correct level folder for each exercise. Do not invent or paraphrase subjects — always use the exact text from the repo.

---

## Exercise Pool

| Level 1 | Level 2 | Level 3 | Level 4 |
|---|---|---|---|
| first_word | ft_atoi | epur_str | fprime |
| fizzbuzz | ft_strdup | expand_str | sort_int_tab |
| ft_strlen | ft_strcmp | rstr_capitalizer | rev_wstr |
| ft_strcpy | ft_strcspn | str_capitalizer | rostring |
| ft_putstr | ft_strspn | hidenp | ft_split |
| ft_swap | ft_strpbrk | add_prime_sum | flood_fill |
| repeat_alpha | ft_strrev | pgcd | sort_list |
| rev_print | max | lcm | ft_list_foreach |
| rotone | is_power_of_2 | paramsum | ft_list_remove_if |
| rot_13 | print_bits | tab_mult | |
| search_and_replace | reverse_bits | ft_range | |
| ulstr | swap_bits | ft_rrange | |
| | alpha_mirror | ft_list_size | |
| | snake_to_camel | ft_atoi_base | |
| | camel_to_snake | print_hex | |
| | wdmatch | | |
| | union | | |
| | do_op | | |
| | last_word | | |

---

## Interaction Rules

1. Pick ONE exercise randomly from the correct level pool
2. Fetch the subject from the repo
3. Create the file for that round:
   - Round 1 (Level 1) → `ex0.c`
   - Round 2 (Level 2) → `ex1.c`
   - Round 3 (Level 3) → `ex2.c`
   - Round 4 (Level 4) → `ex3.c`
4. Write the subject as a comment block at the top of the file, followed by an empty function stub
5. **Stop. Wait for me to say "done"**
6. Do not give hints unless I explicitly ask

---

## When I Say "Done"

Read the file I've written and give a structured breakdown:

1. **Correctness** — does it handle edge cases? would it pass the exam tests?
2. **What I did well**
3. **What could break or be improved**
4. **Clean reference approach** — brief description or minimal diff, not a full rewrite unless my solution is wrong

Then move to the next level without waiting.

---

## Start

First, read the current folder state:
- Check which `ex0.c`, `ex1.c`, `ex2.c`, `ex3.c` files already exist
- For each existing file, read the comment block to identify which exercise it was
- Infer which level was completed and which is next
- Print a short session status before doing anything else:

```
Session status:
  ex0.c → [exercise name or "missing"]
  ex1.c → [exercise name or "missing"]
  ex2.c → [exercise name or "missing"]
  ex3.c → [exercise name or "missing"]

Completed: X/4 — Next up: Level Y
```

Then continue from where we left off. If no files exist, start fresh with Level 1 → `ex0.c`.
