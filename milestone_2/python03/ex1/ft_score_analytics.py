#!/usr/bin/env python3

import sys


def ft_draw_chart(scores: list, average: float, height: int = 22) -> None:
    G  = "\033[92m"   # bright green  (trend line)
    DG = "\033[2;32m" # dim green     (fill)
    YL = "\033[93m"   # yellow        (average)
    CY = "\033[96m"   # cyan          (high score)
    RD = "\033[91m"   # red           (low score)
    WH = "\033[97m"   # white         (labels)
    RS = "\033[0m"    # reset

    n = len(scores)
    max_s = max(scores)
    min_s = min(scores)
    span = max_s - min_s if max_s != min_s else 1
    col_w = 8
    top_pad = 2

    def to_row(v: float) -> int:
        return top_pad + height - 1 - round((v - min_s) / span * (height - 1))

    point_rows = [to_row(s) for s in scores]
    avg_row = to_row(average)
    high_row = to_row(max_s)
    low_row  = to_row(min_s)
    total_h = height + top_pad
    total_w = (n - 1) * col_w + 1

    grid  = [[' '] * total_w for _ in range(total_h)]
    color = [[RS]  * total_w for _ in range(total_h)]

    for x in range(total_w):
        li = min(x // col_w, n - 2)
        t = (x - li * col_w) / col_w
        r_cur = round(point_rows[li] * (1 - t) + point_rows[li + 1] * t)
        slope = point_rows[li + 1] - point_rows[li]
        line_char = '/' if slope < 0 else ('\\' if slope > 0 else '─')

        if x > 0:
            li_p = min((x - 1) // col_w, n - 2)
            t_p = ((x - 1) - li_p * col_w) / col_w
            r_prev = round(point_rows[li_p] * (1 - t_p) + point_rows[li_p + 1] * t_p)
            r_min, r_max = min(r_cur, r_prev), max(r_cur, r_prev)
            grid[r_cur][x] = line_char
            color[r_cur][x] = G
            for r in range(r_min, r_max):
                if grid[r][x] == ' ':
                    grid[r][x] = '│'
                    color[r][x] = G
        else:
            grid[r_cur][x] = line_char
            color[r_cur][x] = G

        for r in range(r_cur + 1, total_h):
            if grid[r][x] == ' ':
                grid[r][x] = '·'
                color[r][x] = DG

    for i, (score, r) in enumerate(zip(scores, point_rows)):
        if score == max_s:
            grid[r][i * col_w] = '▲'
            color[r][i * col_w] = CY
        elif score == min_s:
            grid[r][i * col_w] = '▼'
            color[r][i * col_w] = RD
        else:
            grid[r][i * col_w] = '●'
            color[r][i * col_w] = G

    for i, (score, r) in enumerate(zip(scores, point_rows)):
        label = str(int(score))
        x_start = max(0, min(i * col_w - len(label) // 2, total_w - len(label)))
        label_row = r - 1
        lc = CY if score == max_s else (RD if score == min_s else WH)
        for j, ch in enumerate(label):
            gx = x_start + j
            if 0 <= gx < total_w and 0 <= label_row < total_h:
                grid[label_row][gx] = ch
                color[label_row][gx] = lc

    for x in range(total_w):
        if grid[avg_row][x] in (' ', '·'):
            grid[avg_row][x] = '─'
            color[avg_row][x] = YL

    suffixes = {
        high_row: CY + f"  ▲ HIGH  {int(max_s)}" + RS,
        low_row:  RD + f"  ▼ LOW   {int(min_s)}" + RS,
        avg_row:  YL + f"  ─ AVG   {average:.1f}" + RS,
    }

    print("\n=== Score Chart ===\n")
    for r in range(total_h):
        if r < top_pad:
            axis = "       "
        else:
            val = max_s - ((r - top_pad) / (height - 1)) * span
            axis = f"{val:5.0f} │"
        row_str = ''.join(color[r][x] + grid[r][x] + RS for x in range(total_w))
        print(axis + row_str + suffixes.get(r, ""))

    print("      └" + "─" * total_w)
    xlabels = "       "
    for i in range(n):
        tag = f"P{i + 1}"
        xlabels += tag + " " * (col_w - len(tag))
    print(xlabels)


def ft_score_analytics() -> None:
    print("=== Player Score Analytics ===")
    if len(sys.argv) == 1:
        print("No scores provided. Usage: python3 ft_score_analytics.py <score1> <score2> ...")
        return
    else:
        scores = []
        for i in range(1, len(sys.argv)):
            try:
                score = float(sys.argv[i])
                scores.append(score)
            except ValueError:
                print(f"Invalid score '{sys.argv[i]}'. Please provide numeric values.")
                return
        if scores:
            average_score = sum(scores) / len(scores)
            print(f"Scores processed: {[f'{s:.0f}' for s in scores]}")
            print(f"Total Players: {len(scores)}")
            print(f"Average Score: {average_score:.2f}")
            print(f"High Score: {max(scores):.0f}")
            print(f"Low Score: {min(scores):.0f}")
            print(f"Score Range: {max(scores) - min(scores):.0f}")
            ft_draw_chart(scores, average_score)


if __name__ == "__main__":
    ft_score_analytics()
