"""
SIGNAL: Verifiable Anonymous Salary Sharing Protocol

Demonstration / reference implementation — not for production deployment.

"Know what others earn. Without anyone knowing what YOU earn."

Usage:
    from signal import SignalProtocol, EmployerIdentity, EmployeeIdentity
    
    protocol = SignalProtocol()
    
    # Employers register
    employer = EmployerIdentity("TechCorp")
    protocol.register_employer(employer)
    
    # Employees get attestations (these already exist for banks/taxes)
    employee = EmployeeIdentity("Anonymous")
    attestation = protocol.create_attestation(
        employer, employee,
        annual_salary_cents=75000_00,
        currency="EUR",
        role_category="Software Engineer",
        experience_level="Senior",
        location="Berlin"
    )
    
    # Submit anonymous proof
    proof = protocol.submit_anonymous_proof(attestation)
    
    # Query aggregates (anyone can do this)
    result = protocol.query_salaries(
        role="Software Engineer",
        level="Senior",
        location="Berlin"
    )
    print(f"Median: {result.median / 100} EUR")

Author: chrismaghuhn
License: MIT
"""

from .signal import (
    EmployerIdentity,
    EmployeeIdentity,
    SalaryAttestation,
    SalaryRangeProof,
    AggregateQuery,
    AggregateResult,
    SignalProtocol,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'EmployerIdentity',
    'EmployeeIdentity',
    'SalaryAttestation',
    'SalaryRangeProof',
    'AggregateQuery',
    'AggregateResult',
    'SignalProtocol',
]
