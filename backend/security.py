from qdrant_client import models
from .models import User

def build_qdrant_security_filter(user: User) -> models.Filter:
    must = [
        models.FieldCondition(
            key="tenant_id",
            match=models.MatchValue(value=user.tenant_id),
        ),
        models.FieldCondition(
            key="roles_allowed",
            match=models.MatchAny(any=[user.role]),
        ),
    ]

    must_not = []
    if user.role != "admin":
        must_not.append(
            models.FieldCondition(
                key="sensitive",
                match=models.MatchValue(value=True),
            )
        )

    acl_should = []

    acl_should.append(models.FieldCondition(
        key="allowed_users",
        match=models.MatchAny(any=[user.user_id]),
    ))

    if user.groups:
        acl_should.append(models.FieldCondition(
            key="allowed_groups",
            match=models.MatchAny(any=user.groups),
        ))

    acl_should.append(models.IsEmptyCondition(is_empty=models.PayloadField(key="allowed_users")))
    acl_should.append(models.IsEmptyCondition(is_empty=models.PayloadField(key="allowed_groups")))

    return models.Filter(
        must=must,
        must_not=must_not,
        should=acl_should,
        min_should=1,
    )
