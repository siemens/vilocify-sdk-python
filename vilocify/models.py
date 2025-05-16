"""Model definitions for the Vilocify API"""

#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

from vilocify.jsonapy import Action, Attribute, Model, RelationshipToMany, RelationshipToOne


class Component(Model):
    vendor = Attribute[str | None]("vendor")
    name = Attribute[str | None]("name")
    version = Attribute[str | None]("version")
    url = Attribute[str | None]("url")
    created_at = Attribute[str]("createdAt")
    updated_at = Attribute[str]("updatedAt")
    eol_on = Attribute[str | None]("endOfLifeOn")
    is_eol = Attribute[bool]("endOfLife")
    active = Attribute[bool]("active")
    deactivated_at = Attribute[str | None]("deactivatedAt")
    deactivation_reason = Attribute[str | None]("deactivationReason")

    monitoring_lists: RelationshipToMany["MonitoringList"] = RelationshipToMany("MonitoringList")
    notifications: RelationshipToMany["Notification"] = RelationshipToMany("Notification")


class Membership(Model):
    username = Attribute[str]("userName", serialize_on=(Action.CREATE,))
    email = Attribute[str]("userEmail", serialize_on=(Action.CREATE,))
    role = Attribute[str]("role", serialize_on=(Action.CREATE,))
    expires_at = Attribute[str | None]("expiresAt")
    invitation_state = Attribute[str]("invitationState", serialize_on=())
    created_at = Attribute[str]("createdAt", serialize_on=())
    updated_at = Attribute[str]("updatedAt", serialize_on=())


class ComponentRequest(Model):
    vendor = Attribute[str | None]("vendor")
    name = Attribute[str]("name")
    version = Attribute[str]("version")
    comment = Attribute[str | None]("comment")
    prioritized = Attribute[bool]("prioritized")
    security_url = Attribute[str | None]("securityUrl")
    component_url = Attribute[str | None]("componentUrl")
    state = Attribute[str]("state", serialize_on=())
    rejection_reasons = Attribute[list[str] | None]("rejectionReasons", serialize_on=())
    created_at = Attribute[str]("createdAt", serialize_on=())
    updated_at = Attribute[str]("updatedAt", serialize_on=())

    component = RelationshipToOne(Component)
    membership = RelationshipToOne(Membership)


class Vulnerability(Model):
    @classmethod
    def jsonapi_type_name(cls) -> str:
        return "vulnerabilities"

    cve = Attribute[str | None]("cve")
    cwe = Attribute[str | None]("cwe")
    description = Attribute[str]("description")
    cvss = Attribute[list[dict]]("cvss")
    mitigating_factor = Attribute[str | None]("mitigatingFactor")
    note = Attribute[str | None]("note")
    deleted = Attribute[bool]("deleted")


class Notification(Model):
    title = Attribute[str]("title")
    priority = Attribute[str]("priority")
    action = Attribute[str]("action")
    solution = Attribute[str]("solution")
    description = Attribute[str]("description")
    vendor_affected_components = Attribute[str]("vendorAffectedComponents")
    references = Attribute[list[str]]("references")
    advisories = Attribute[list[dict[str, str]]]("advisories")
    cves = Attribute[list[str]]("cves")
    attack_vector = Attribute[str | None]("attackVector")
    cvss = Attribute[str | None]("cvss")
    history = Attribute[list[dict]]("history")
    type = Attribute[str]("type")
    third_party_published_on = Attribute[str]("thirdPartyPublishedOn")
    created_at = Attribute[str]("createdAt")
    updated_at = Attribute[str]("updatedAt")

    vulnerabilities = RelationshipToMany(Vulnerability)
    components = RelationshipToMany(Component)


class MonitoringList(Model):
    MAX_COMPONENTS = 1000

    name = Attribute[str]("name")
    comment = Attribute[str | None]("comment")
    active = Attribute[bool]("active")
    created_at = Attribute[str]("createdAt", serialize_on=())
    updated_at = Attribute[str]("updatedAt", serialize_on=())

    components = RelationshipToMany(Component)
    subscriptions: RelationshipToMany["Subscription"] = RelationshipToMany("Subscription")
    parents: RelationshipToMany["MonitoringList"] = RelationshipToMany("MonitoringList", "parents")
    children: RelationshipToMany["MonitoringList"] = RelationshipToMany("MonitoringList", "children")


class Subscription(Model):
    role = Attribute[str]("role")
    priorities = Attribute[list[str]]("priorities")
    created_at = Attribute[str]("createdAt", serialize_on=())
    updated_at = Attribute[str]("updatedAt", serialize_on=())

    membership = RelationshipToOne(Membership)
    monitoring_list = RelationshipToOne(MonitoringList)
