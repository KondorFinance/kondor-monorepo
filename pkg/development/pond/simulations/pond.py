from dataclasses import dataclass
from re import X
from time import clock_getres
from tkinter import Y
import numpy as np
from copy import copy

# Python impl of constant product


@dataclass
class ConstantProductInvariant:
    a_supply: int
    b_supply: int

    max_pool_supply: int
    pool_supply: int

    scale: int
    fee: int

    _A: int
    A_PRECISION: int

    def mint(self, a: int, b: int) -> int:
        a_rat = (a * self.scale) // self.a_supply
        b_rat = (b * self.scale) // self.b_supply

        # Use the min of the 2 scaled assets
        to_mint = (min(a_rat, b_rat) * self.issued()) // self.scale

        if to_mint == 0:
            return 0

        # compute first, then tweak balances
        self.a_supply += a
        self.b_supply += b
        self.pool_supply -= to_mint

        return to_mint

    def burn(self, amount) -> tuple[int, int]:
        burn_a = (self.a_supply * amount) // self.issued()
        burn_b = (self.b_supply * amount) // self.issued()

        if burn_a == 0 or burn_b == 0:
            return 0, 0

        # computed first, then tweak balances
        self.a_supply -= burn_a
        self.b_supply -= burn_b
        self.pool_supply += amount

        return burn_a, burn_b

    def swap(self, amount: int, is_a: bool) -> int:

        if is_a:
            swap_amt = self._get_tokens_to_swap(amount, self.a_supply, self.b_supply, 0 , 1)
            if swap_amt == 0:
                return 0
            self.a_supply += amount
            self.b_supply -= swap_amt
            return swap_amt

        # swap_amt = self._get_tokens_to_swap(amount, self.b_supply, self.a_supply, 1, 0)
        swap_amt = self._get_tokens_to_swap(amount, self.a_supply, self.b_supply, 1 , 0)
        if swap_amt == 0:
            return 0

        self.b_supply += amount
        self.a_supply -= swap_amt
        return swap_amt

    def _get_tokens_to_swap(self, in_amount, in_supply, out_supply, tokenIndexFrom, tokenIndexTo) -> int:
        assert in_supply > 0
        assert out_supply > 0
        """ Stable swap method for n stable assets, 
            it combines the sum formula and the constant product formula,
            the generalized expresion for n number of stable asstes:

            X + Y  + (X * Y) = D + (D^n / n)

            Where:
            n is the number of stable asstes
            D is the total number of coins when they have an equal price
            X, Y are current supply of assets
        """

        print('in: ', in_amount, 'X: ', in_supply, 'Y: ', out_supply)
        x = in_amount + in_supply
        xp = [in_supply, out_supply]
        # d = self._calculate_d(in_supply, out_supply)
        # print('D_org: ', d)
        y = self._calculate_Y(x, in_supply, out_supply, tokenIndexFrom, tokenIndexTo)
        # print('y: ', y)
        y_out = (xp[tokenIndexTo] - y)

        print('Y final: ', y_out)
        fee = self.fee / self.scale
        print('fee: ', fee)
        y_fee = y_out * fee
        out_amt = y_out - y_fee
        print ('out_amt: ', out_amt)
        if (out_amt < 0):
            return y_out
        print('in: ', in_amount, 'X: ', in_supply, 'Y: ', out_supply, 'out: ', out_amt)
        return int(out_amt)
    
    def _calculate_d(self, in_supply, out_supply):
        A = self._A * self.A_PRECISION
        xp = [in_supply, out_supply]
        nT = len(xp)
        s = 0
        for i in range(nT):
            s = s + xp[i]
        if s == 0:
            return 0

        prevD = 0
        d = s
        nA = A * nT

        for i in range(255):
            dp = d
            for j in range (nT):
                dp = ((dp * d) / (xp[j] * nT + 1))

            prevD = d
            d = ((
                (((nA * s) / self.A_PRECISION) + (dp * nT)) * d
                ) / (
                (((nA - self.A_PRECISION) * d) / self.A_PRECISION) + ((nT + 1) * dp)
                ))        
            if (self._within1(d, prevD)):
                return d
        return 0
    
    def _calculate_Y (self, x, in_supply, out_supply, tokenIndexFrom = 0, tokenIndexTo = 1):
        print('AT Y calc ---- in: ', x, 'X: ', in_supply, 'Y: ', out_supply)
        A = self._A * self.A_PRECISION
        xp = [in_supply, out_supply]
        nT = len(xp)
        d = self._calculate_d(in_supply, out_supply)
        print('D: ', d)
        c = d
        s = 0
        nA = nT * A
        _x = 0

        for i in range(nT):
            if (i == tokenIndexFrom):
                _x = x
            elif (i != tokenIndexTo):
                _x = xp[i]
            else:
                continue
            s = s + _x
            c = (c * d) / (_x * nT + 1)

        z = in_supply * out_supply
        c = ((c * d) * self.A_PRECISION) / (nA * nT)
        b = s + ((d * self.A_PRECISION) / nA)
        yPrev = 0
        y = d
    
        for i in range(255):
            yPrev = y
            y = ((y * y) + c) / (((y * 2) + b) - d)
            if (self._within1(y, yPrev)):
                return y
        return 0
    
    def _within1 (self, a, b):
        return self._difference(a, b) <= 1
    
    def _difference (self, a, b):
        if (a > b):
            return a - b
        return b - a
    
    def _calculate_chi_factor(self, in_supply, out_supply):
        return (self.a_coef * (in_supply * out_supply)) / (
            (self._calculate_d(in_supply, out_supply) / 2) ** 2
        )

    def scaled_ratio(self) -> int:
        return int(self.ratio() * self.scale)

    def issued(self) -> int:
        return self.max_pool_supply - self.pool_supply

    def ratio(self):
        return self.a_supply / self.b_supply


class Simulator:
    def __init__(self):
        self.cpi = ConstantProductInvariant(
            a_supply=int(1e6),
            b_supply=int(1e6),
            max_pool_supply=int(1e9),
            pool_supply=int(1e9) - 100000,
            scale=1000,
            fee=3,
            _A = 10,
            A_PRECISION = 100,
            # xp = [self.a_supply, self.b_supply
        )

        self.states = []

    def run_mints(self, num: int = 100):
        self.sizes = np.random.randint(100, 1000, num)
        for size in self.sizes:
            # force them to be the right ratio
            a_size = size * self.cpi.ratio()
            b_size = size

            self.cpi.mint(a_size, b_size)
            self.states.append(copy(self.cpi))

    def run_burns(self, num: int = 100):
        self.sizes = np.random.randint(100, 10000000, num)
        for size in self.sizes:
            # Get a reasonable size given number of issued tokens
            # should be ~ 1% --> 0.0001% burns
            size = self.cpi.issued() // size
            self.cpi.burn(size)
            self.states.append(copy(self.cpi))

    def run_swaps(self, num: int = 100):

        self.sizes = np.random.randint(10, 1000, num)
        for idx, size in enumerate(self.sizes):
            a_swap = (idx + size) % 2 == 0
            # Re-size if its an a_swap
            size *= self.cpi.ratio() if a_swap else 1
            _ = self.cpi.swap(size, a_swap)
            self.states.append(copy(self.cpi))

    def run_mix(self, num=100):
        nums = np.random.randint(1, 4, num)
        for idx, runs in enumerate(nums):
            v = (idx + runs) % 3
            match v:
                case 0:
                    self.run_mints(runs)
                case 1:
                    self.run_burns(runs)
                case 2:
                    self.run_swaps(runs)

    def get_states_for(self, k: str) -> list[int]:
        if hasattr(self.cpi, k):
            return [getattr(c, k) for c in self.states]
        return []

    def get_states(self) -> dict[str, list[int]]:
        states: dict[str, list[int]] = {}
        for key in self.cpi.__annotations__.keys():
            states[key] = self.get_states_for(key)

        del states["scale"]
        del states["fee"]
        del states["max_pool_supply"]

        states["ratio"] = [s.ratio() for s in self.states]
        return states