"""ESBOZO — Entry point de la app CDK.

    cd infrastructure/cdk
    pip install -r requirements.txt
    cdk synth      # genera la plantilla CloudFormation (no despliega)
    cdk deploy     # requiere credenciales AWS + `cdk bootstrap`

Coherente con DEC-002 (IaC = CDK v2 Python).
"""
from __future__ import annotations

import aws_cdk as cdk

from precompute_stack import PrecomputeStack

app = cdk.App()
PrecomputeStack(app, "IntegraPrecompute")
app.synth()
