def is_cpf(cpf: str) -> bool:
    if len(cpf) != 11:
        return False
    
    if not cpf.isascii() or not cpf.isdecimal():
        return False

    if len(set(cpf)) == 1:
        return False
 
    return _dv_validator(cpf)

def _calculate_dv(digits: str, initial_weight: int) -> int:
    total = 0

    for digit, weight in zip(digits, range(initial_weight, 1, -1)):
        total += int(digit) * weight

    total = total % 11

    if total < 2:
        return 0

    return 11 - total

def _dv_validator(cpf: str) -> bool:
    nine_digits = cpf[0:9]
    two_digits = cpf[-2:]

    dv1 = _calculate_dv(nine_digits, 10)

    cpf_ten = nine_digits + str(dv1)

    dv2 = _calculate_dv(cpf_ten, 11)

    return dv1 == int(two_digits[0]) and dv2 == int(two_digits[1])
    