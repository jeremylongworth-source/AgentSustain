"""Bounded annual IRR roots via derivative partitioning of the NPV polynomial."""
from decimal import Decimal, localcontext

from .data_tools import number, serialize


def irr_roots(cashflows, search):
    fields = {"lower_percent", "upper_percent", "rate_tolerance_percent", "npv_tolerance", "max_iterations"}
    if not isinstance(search, dict) or set(search) != fields:
        raise ValueError("Explicit IRR bounds, rate/NPV tolerances and iteration budget required.")
    lower, upper = number(search["lower_percent"]), number(search["upper_percent"])
    rate_tol, npv_tol = number(search["rate_tolerance_percent"]), number(search["npv_tolerance"])
    iterations = search["max_iterations"]
    if (not -100 < lower < upper or rate_tol <= 0 or npv_tol <= 0
            or isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 1000):
        raise ValueError("IRR bounds must exceed -100%, tolerances positive, and iteration budget 1..1000.")
    coefficients = [number(value) for value in cashflows]
    if not 2 <= len(coefficients) <= 61:
        raise ValueError("Supported annual IRR polynomial requires 1..60 explicit future years.")
    with localcontext() as context:
        context.prec = 70
        scale = sum(abs(c) for c in coefficients)
        if scale == 0:
            return {"code": "IRR_INDETERMINATE", "roots": [], "sign_changes": 0,
                    "message": "All cash flows are zero; every admissible rate satisfies NPV=0, so IRR is indeterminate."}, None
        if rate_tol > Decimal("0.000001") or npv_tol > scale*Decimal("0.00000001"):
            raise ValueError("Use rate tolerance <= 0.000001 percentage points and NPV tolerance <= 1e-8 of absolute flow sum.")
        signs = [1 if c > 0 else -1 for c in coefficients if c != 0]
        changes = sum(a != b for a, b in zip(signs, signs[1:]))
        # x=1/(1+r): roots of sum(CF_t*x^t) on a positive bounded x interval.
        lower_denominator, upper_denominator = 1+lower/100, 1+upper/100
        if lower_denominator <= 0 or upper_denominator <= 0:
            raise ValueError("IRR bound is too close to -100% for the supported numerical precision.")
        xmin, xmax = 1/upper_denominator, 1/lower_denominator
        xtol = min(Decimal("1e-26"), rate_tol/100*xmin*xmin/4)

        def evaluate(poly, x):
            value = Decimal(0)
            for coefficient in reversed(poly): value = value*x+coefficient
            return value

        def near_zero(poly, x):
            # Tight internal roundoff threshold, distinct from the user's
            # currency residual tolerance. Tangent candidates are also verified.
            magnitude = sum(abs(c) for c in poly)*max(Decimal(1), abs(x))**(len(poly)-1)
            return abs(evaluate(poly, x)) <= magnitude*Decimal("1e-45")

        def isolate(poly):
            poly = list(poly)
            while len(poly) > 1 and poly[-1] == 0: poly.pop()
            if len(poly) <= 1: return []
            if len(poly) == 2:
                root = -poly[0]/poly[1]
                return [root] if xmin <= root <= xmax else []
            critical = isolate([i*poly[i] for i in range(1, len(poly))])
            points = sorted(set([xmin]+critical+[xmax]))
            roots = [x for x in points if near_zero(poly, x)]
            for left, right in zip(points, points[1:]):
                fleft, fright = evaluate(poly, left), evaluate(poly, right)
                if fleft*fright >= 0 or near_zero(poly, left) or near_zero(poly, right): continue
                for _ in range(iterations):
                    middle = (left+right)/2
                    fmiddle = evaluate(poly, middle)
                    if fmiddle == 0: left = right = middle; break
                    if fleft*fmiddle < 0: right = middle
                    else: left, fleft = middle, fmiddle
                    if right-left <= xtol: break
                else:
                    raise ValueError("IRR derivative-partition root isolation did not converge within the supplied iteration budget.")
                roots.append((left+right)/2)
            unique = []
            for root in sorted(roots):
                if not unique or abs(root-unique[-1]) > xtol*4: unique.append(root)
            return unique

        candidates = isolate(coefficients)
        verified = []
        raw_rates = []
        for x in candidates:
            rate = (1/x-1)*100
            residual = evaluate(coefficients, x)
            if not lower <= rate <= upper or abs(residual) > npv_tol:
                raise ValueError("IRR candidate fails the supplied rate-bound or NPV residual tolerance.")
            serialized_rate = serialize(rate)
            serialized_x = 1/(1+number(serialized_rate)/100)
            serialized_residual = evaluate(coefficients, serialized_x)
            if abs(number(serialized_rate)-rate) > rate_tol or abs(serialized_residual) > npv_tol:
                raise ValueError("IRR JSON serialization cannot meet the supplied rate/NPV tolerance.")
            verified.append({"rate_percent": serialized_rate, "npv_residual": serialize(serialized_residual)})
            raw_rates.append(rate)
        verified.sort(key=lambda root: root["rate_percent"])
        report = {"code": "IRR_ROOT_SEARCH", "roots": verified, "sign_changes": changes,
                  "search": search, "method": "70-digit Decimal derivative partitioning and bisection in x=1/(1+r)",
                  "scope": "Numerical candidates within supplied rate bounds; nonconventional cash flows do not establish global uniqueness."}
        if not verified:
            report.update(code="IRR_ROOT_NOT_FOUND", message="No verified IRR candidate within the supplied bounds; do not infer no root outside them.")
        elif len(verified) > 1:
            report.update(code="IRR_MULTIPLE_ROOTS", message="Multiple verified IRR candidates; no single return selected.")
        elif changes != 1:
            report.update(code="IRR_GLOBAL_UNIQUENESS_UNPROVEN", message="One bounded candidate for nonconventional flows; global uniqueness is unproven and no single IRR is emitted.")
        else:
            report.update(message="One verified candidate; one sign change establishes at most one positive-x root, equivalent to one rate above -100%.")
            return report, raw_rates[0]
        return report, None
