from langchain_core.tools import tool
from data.knowledge_base import BEST_PRACTICES, COMPLIANCE_RULES


@tool
def search_best_practices(topic: str, category: str) -> str:
    """Search best-practice guidance for a cloud infrastructure topic.

    Look up authoritative best practices from the internal knowledge base.
    Call this first when answering an infrastructure question.

    Args:
        topic: The cloud service or technology (e.g. 'S3', 'IAM', 'VPC', 'EC2',
               'RDS', 'Lambda', 'Terraform', 'Kubernetes').
        category: The type of guidance needed (e.g. 'security', 'cost',
                  'state management').
    """
    key = (topic.lower(), category.lower())
    result = BEST_PRACTICES.get(key)
    if result:
        return result

    # Partial match: return the first entry whose topic matches, ignoring category.
    for (t, _c), v in BEST_PRACTICES.items():
        if t == topic.lower():
            return v

    available = sorted({t for t, _c in BEST_PRACTICES})
    return (
        f"No best practices found for topic='{topic}', category='{category}'. "
        f"Available topics: {', '.join(available)}."
    )


@tool
def check_compliance_rules(service: str, rule_type: str) -> str:
    """Check compliance and regulatory rules for a cloud service.

    Returns relevant control mappings from CIS Benchmarks, AWS Well-Architected
    Framework, or NIST SP 800-53. Call this after search_best_practices to add
    the compliance dimension to your research.

    Args:
        service: The AWS service or technology (e.g. 'S3', 'IAM', 'VPC', 'EC2',
                 'RDS', 'Lambda', 'Terraform', 'Kubernetes').
        rule_type: The compliance framework to look up. One of:
                   'cis'             — CIS AWS Foundations Benchmark
                   'well_architected' — AWS Well-Architected Framework
                   'nist'            — NIST SP 800-53 Rev 5
    """
    key = (service.lower(), rule_type.lower())
    result = COMPLIANCE_RULES.get(key)
    if result:
        return result

    # Partial match: return the first compliance entry whose service matches.
    for (s, _r), v in COMPLIANCE_RULES.items():
        if s == service.lower():
            return v

    available = sorted({s for s, _r in COMPLIANCE_RULES})
    return (
        f"No compliance rules found for service='{service}', rule_type='{rule_type}'. "
        f"Available services: {', '.join(available)}."
    )


@tool
def format_report(
    question: str,
    best_practices: list[str],
    compliance_rules: list[str],
) -> str:
    """Format collected research into a structured Markdown advisory report.

    Call this tool once you have gathered sufficient best practices and compliance
    rules. Pass the key findings as lists of concise bullet-point strings extracted
    from your research.

    Args:
        question: The original question asked by the user.
        best_practices: Key best-practice points gathered (each item is one bullet point).
        compliance_rules: Compliance rule strings gathered (each item is one rule or control).
    """
    bp_section = (
        "\n".join(f"- {bp.strip()}" for bp in best_practices)
        if best_practices
        else "- No best practices retrieved."
    )
    cr_section = (
        "\n".join(f"- {cr.strip()}" for cr in compliance_rules)
        if compliance_rules
        else "- No compliance rules retrieved."
    )

    return (
        f"## Cloud Infrastructure Advisory Report\n\n"
        f"**Question:** {question}\n\n"
        f"---\n\n"
        f"### Best Practices\n"
        f"{bp_section}\n\n"
        f"---\n\n"
        f"### Compliance Requirements\n"
        f"{cr_section}\n\n"
        f"---\n\n"
        f"### Recommended Next Steps\n"
        f"- Audit your current configuration against the findings above.\n"
        f"- Run AWS Config conformance packs or Security Hub standards to detect gaps.\n"
        f"- Prioritise controls by risk level (critical > high > medium).\n"
        f"- Document any accepted exceptions with compensating controls and owner sign-off.\n"
        f"- Schedule a quarterly review to keep the advisory current.\n"
    )
