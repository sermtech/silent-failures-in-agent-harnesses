"""SIMULATION ONLY -- no network, no real endpoint is contacted.

Generic round-robin A/B: arms are callables returning True (request failed).
Demonstrates why n=1 or blocked (A-then-B) comparisons against a flaky endpoint
whose failure rate DRIFTS over time can give a wrong conclusion, while
interleaving the arms (same minutes) with n>=12 does not.

Method generalised from probe_session_header.py in the source project.
Run: python -X utf8 roundrobin_ab.py
"""
import math
import random

N = 12          # requests per arm for the n>=12 methods
THRESH = 4      # n>=12 methods declare "differs" only if fail counts differ by >= THRESH
TRIALS = 2000
SEED = 20261018


def make_endpoint(rng, effect_b):
    """Flaky endpoint: base failure rate drifts sinusoidally with the clock
    (range 0.10..0.80, period 40 'minutes', random phase). Arm B adds effect_b."""
    phase = rng.uniform(0, 2 * math.pi)
    clock = [0]

    def p(t):
        return 0.45 + 0.35 * math.sin(2 * math.pi * t / 40 + phase)

    def arm(extra):
        def call():
            t = clock[0]
            clock[0] += 1  # every request takes one simulated minute
            return rng.random() < min(1.0, p(t) + extra)
        return call

    return arm(0.0), arm(effect_b)


def run_arms(method, a, b, n):
    """Return (fails_a, fails_b, n_per_arm) for a scheduling method."""
    if method == "n=1":
        return int(a()), int(b()), 1
    if method == "blocked":          # all of A, then all of B
        fa = sum(a() for _ in range(n))
        fb = sum(b() for _ in range(n))
        return fa, fb, n
    fa = fb = 0                      # interleaved: A,B,A,B,... same minutes
    for _ in range(n):
        fa += a()
        fb += b()
    return fa, fb, n


def verdict(fa, fb, n):
    d = fb - fa
    need = 1 if n == 1 else THRESH
    return "B_worse" if d >= need else "A_worse" if -d >= need else "no_diff"


def scenario(name, effect_b):
    print(f"\n--- {name} (B adds {effect_b:+.2f} to failure prob; {TRIALS} trials) ---")
    print(f"{'method':<12}{'B_worse':>9}{'A_worse':>9}{'no_diff':>9}")
    for method in ("n=1", "blocked", "interleaved"):
        rng = random.Random(SEED)    # same seed per method: same drift draws
        tally = {"B_worse": 0, "A_worse": 0, "no_diff": 0}
        for _ in range(TRIALS):
            a, b = make_endpoint(rng, effect_b)
            tally[verdict(*run_arms(method, a, b, N))] += 1
        print(f"{method:<12}" + "".join(f"{100*tally[k]/TRIALS:8.1f}%" for k in tally))


if __name__ == "__main__":
    print("SIMULATION (synthetic drifting endpoint, seed", SEED, ") -- not real data")
    scenario("NULL: arms truly identical, correct answer = no_diff", 0.0)
    scenario("REAL: B truly worse, correct answer = B_worse", 0.30)
    print("\nWrong-sign verdicts (A_worse when B is worse) and false alarms in the NULL "
          "scenario are the conclusion flips.")
