from prompt_validator.core.contracts import Finding, GuardConfig, MaskMode


def mask(
    original_text: str, findings: tuple[Finding, ...], config: GuardConfig
) -> tuple[str, dict[str, str]]:
    masked_parts: list[str] = []
    replacements: dict[str, str] = {}

    placeholder_by_value: dict[tuple[str, str], str] = {}
    placeholder_counter: dict[str, int] = {}

    last_end = 0

    for finding in findings:
        start = finding.start
        end = finding.end

        before_finding = original_text[last_end:start]
        masked_parts.append(before_finding)

        original_value = original_text[start:end]
        finding_type = finding.matched_type.upper()

        key = (finding_type, original_value)

        if key in placeholder_by_value:
            placeholder = placeholder_by_value[key]
        else:
            placeholder_counter[finding_type] = (
                placeholder_counter.get(finding_type, 0) + 1
            )
            placeholder = f"[{finding_type}_{placeholder_counter[finding_type]}]"
            placeholder_by_value[key] = placeholder

            if config.mask_mode == MaskMode.REVERSIBLE:
                replacements[placeholder] = original_value

        masked_parts.append(placeholder)

        last_end = end

    masked_parts.append(original_text[last_end:])
    masked_text = "".join(masked_parts)

    return masked_text, replacements


def rehydrate(masked_text: str, replacements: dict[str, str]) -> str:
    rehydrated_text = masked_text

    for placeholder, original_value in replacements.items():
        rehydrated_text = rehydrated_text.replace(placeholder, original_value)

    return rehydrated_text
