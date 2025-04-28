"""jsonapy implements a lazy JSON:API client that supports cursor pagination."""

#  SPDX-FileCopyrightText: 2025 Siemens AG
#  SPDX-License-Identifier: MIT

import abc
from collections.abc import Iterable, Iterator
from enum import Enum
from itertools import islice
from typing import Any, ClassVar, NamedTuple, Self
from urllib.parse import urlparse

from vilocify import JSON, api_config, http

JSONDict = dict[str, JSON]
Meta = JSONDict | None


class Relationship[RelModel: "Model"](abc.ABC):
    def __init__(self, target_type: type[RelModel] | str, relationship_name: str | None = None):
        self._target_type = target_type
        self._relationship_name = relationship_name

    @property
    def target_type(self) -> type[RelModel]:
        if isinstance(self._target_type, str):
            self._target_type = ModelMeta.__models__[self._target_type]
        return self._target_type

    @property
    def relationship_name(self) -> str:
        if self._relationship_name is None:
            self._relationship_name = self.default_relationship_name(self.target_type)
        return self._relationship_name

    @abc.abstractmethod
    def default_relationship_name(self, target_type: type[RelModel]) -> str:
        pass


class RelationshipToOne[RelModel: "Model"](Relationship[RelModel]):
    def default_relationship_name(self, target_type: type[RelModel]) -> str:
        return target_type.jsonapi_type_name()[:-1]

    def __get__[SelfModel: "Model"](self, obj: SelfModel, objtype: type[SelfModel] | None = None) -> RelModel | None:
        if obj.id is None:
            raise UnmappedModelError("Model is not mapped")
        return Request(obj.__class__).get_one_related(obj.id, self.target_type, self.relationship_name)

    def __set__(self, obj: "Model", value: RelModel) -> None:
        obj._jsonapi_to_one_relationships[self.relationship_name] = value


class Many[RelModel: "Model"]:
    def __init__(self, obj: "Model", target_type: type[RelModel], relationship_name: str) -> None:
        self.obj = obj
        self.target_type = target_type
        self.relationship_name = relationship_name

    def __iter__(self):
        yield from Request(self.obj.__class__).iter_many_related(self.obj.id, self.target_type, self.relationship_name)

    def extend(self, *related: RelModel):
        Request(self.obj.__class__).update_many_related(self.obj, self.relationship_name, *related)

    def iids(self) -> Iterator[str]:
        yield from (m.id for m in self)

    def ids(self) -> list[str]:
        return list(self.iids())


class RelationshipToMany[RelModel: "Model"](Relationship[RelModel]):
    def default_relationship_name(self, target_type: type[RelModel]) -> str:
        return target_type.jsonapi_type_name()

    def __get__[SelfModel: "Model"](self, obj: SelfModel, objtype: type[SelfModel] | None = None) -> Many[RelModel]:
        return Many(obj, self.target_type, self.relationship_name)

    def __set__(self, obj: "Model", value: Iterable[RelModel]) -> None:
        obj._jsonapi_to_many_relationships[self.relationship_name] = value


class Action(Enum):
    CREATE = "create"
    UPDATE = "update"


class Attribute[T]:
    def __init__(self, api_attribute_name: str, serialize_on: tuple[Action, ...] = (Action.CREATE, Action.UPDATE)):
        self.api_attribute_name = api_attribute_name
        self.serialize = serialize_on

    def __get__[TModel: "Model"](self, obj: TModel, objtype: type[TModel] | None = None) -> T:
        if self.api_attribute_name not in obj._jsonapi_attributes:
            obj.refresh()

        return obj._jsonapi_attributes[self.api_attribute_name]

    def __set__[TModel: "Model"](self, obj: TModel, value: T):
        if self.serialize == ():
            raise AttributeError("Cannot set read-only attribute")
        if Action.UPDATE not in self.serialize and self.api_attribute_name in obj._jsonapi_attributes:
            raise AttributeError("Cannot set write-once attribute")
        obj._jsonapi_attributes[self.api_attribute_name] = value


class Serializer[TModel: "Model"]:
    @staticmethod
    def _get_data[T](api_response: JSON, data_type: type[T]) -> T | None:
        if not isinstance(api_response, dict):
            raise DeserializationError("Received invalid JSON:API response")

        data = api_response.get("data")
        if data is None:
            return None

        if not isinstance(data, data_type):
            raise DeserializationError(f"Expected data to be {data_type.__name__}")

        return data

    @staticmethod
    def deserialize_next_link(api_response: JSON) -> str | None:
        if not isinstance(api_response, dict):
            raise DeserializationError("Received invalid JSON:API response")

        links = api_response["links"]
        if not isinstance(links, dict):
            raise DeserializationError("Received invalid JSON:API response. links is not an object")

        next_link = links["next"]
        if next_link is not None and not isinstance(next_link, str):
            raise DeserializationError("Received invalid JSON:API response. The next link is not a string")

        return next_link

    @staticmethod
    def deserialize_one(target_cls: type[TModel], api_response: JSON) -> TModel | None:
        if api_response is None:
            return None

        if (data := Serializer._get_data(api_response, dict)) is None:
            return None

        if not isinstance(api_response, dict):
            raise DeserializationError("Received invalid JSON:API response")

        obj = target_cls()
        obj._id = data["id"]

        included = api_response.get("included", None)
        if included is not None and not isinstance(included, list):
            raise DeserializationError("Received invalid JSON:API response. `included` must be a list")

        included_attributes: dict = {}
        if included is not None and len(included) == 1:
            included_doc = included[0]
            if (
                isinstance(included_doc, dict)
                and isinstance(included_doc["attributes"], dict)
                and included_doc["id"] == obj._id
                and included_doc["type"] == obj.jsonapi_type_name()
            ):
                included_attributes = included_doc["attributes"]
            else:
                raise DeserializationError("Included document has wrong type or id")

        obj._jsonapi_attributes = data.get("attributes", included_attributes)

        return obj

    @staticmethod
    def deserialize_many(target_cls: type[TModel], api_response: JSON) -> Iterator[TModel]:
        if api_response is None:
            return None

        if (data := Serializer._get_data(api_response, list)) is None:
            return None

        if not isinstance(api_response, dict):
            raise DeserializationError("Received invalid JSON:API response")

        included_response = api_response.get("included", [])

        if not isinstance(included_response, list):
            raise DeserializationError("Received invalid JSON:API response. Included response must be a list")

        included = {(doc["type"], doc["id"]): doc for doc in included_response if isinstance(doc, dict)}

        for item in data:
            included_doc = included.get((item["type"], item["id"]))
            one_data = {"data": item}
            if included_doc is not None:
                one_data["included"] = [included_doc]
            deserialized_item = Serializer.deserialize_one(target_cls, one_data)
            if deserialized_item is not None:
                yield deserialized_item

    @staticmethod
    def serialize_meta(meta: Meta) -> JSONDict:
        if meta is None:
            return {"meta": {}}
        return {"meta": meta}

    @staticmethod
    def serialize_one(obj: "Model", meta: Meta, action: Action) -> JSON:
        attrs = {
            attr.api_attribute_name: obj._jsonapi_attributes[attr.api_attribute_name]
            for name, attr in obj.__class__.__dict__.items()
            if not name.startswith("_")
            and isinstance(attr, Attribute)
            and action in attr.serialize
            and attr.api_attribute_name in obj._jsonapi_attributes
        }

        data: JSONDict = {"type": obj.jsonapi_type_name(), "attributes": attrs}

        if obj.id:
            data["id"] = obj.id

        to_many_relationships: JSONDict = {
            name: {"data": [{"id": item.id, "type": item.jsonapi_type_name()} for item in relationship_data]}
            for name, relationship_data in obj._jsonapi_to_many_relationships.items()
        }
        to_one_relationships: JSONDict = {
            name: {"data": {"id": item.id, "type": item.jsonapi_type_name()}}
            for name, item in obj._jsonapi_to_one_relationships.items()
        }

        relationships = to_many_relationships | to_one_relationships

        if relationships:
            data["relationships"] = relationships

        return_dict: JSONDict = {"data": data}
        if meta:
            return_dict["meta"] = meta

        return return_dict

    @staticmethod
    def serialize_many_related(*related: "Model") -> JSON:
        data: list[JSON] = []
        for item in related:
            if item.id is None:
                raise UnmappedModelError("Related model has no id")
            data.append({"id": item.id, "type": item.jsonapi_type_name()})
        return {"data": data}


class UnmappedModelError(Exception):
    """Raised when trying to send a modifying request for a model instance without an ID."""


class DeserializationError(Exception):
    """Raise when the serializer cannot parse an API response."""


class IllegalSortError(Exception):
    """Raised when attempting unsupported sorting, e.g. a multi-attribute sort."""


def urljoin(base: str, *path: str) -> str:
    if urlparse(base).scheme not in ["http", "https"]:
        raise ValueError("Bad schema in base")

    segments = (segment.strip("/") for segment in path)

    return base.rstrip("/") + "/" + "/".join(segments)


class Filter(NamedTuple):
    attribute: str
    operator: str
    value: str


class Request[TModel: "Model"]:
    def __init__(self, model_class: type[TModel]):
        self.model_class = model_class
        self.filters: list[Filter] = []
        self.sorter: str | None = None
        self._page_size = 100

    @staticmethod
    def _inclusion_params[RelModel: "Model"](
        relationship_name: str, relationship_type: type[RelModel]
    ) -> dict[str, str]:
        params = {"include": relationship_name}
        fields = ",".join(relationship_type._jsonapi_attribute_names)
        if fields:
            params[f"fields[{relationship_type.jsonapi_type_name()}]"] = fields

        return params

    def get(self, resource_id: str) -> TModel:
        jsonapi_type_name = self.model_class.jsonapi_type_name()
        url = urljoin(api_config.base_url, jsonapi_type_name, resource_id)
        params = {}
        fields = ",".join(self.model_class._jsonapi_attribute_names)
        if fields:
            params[f"fields[{jsonapi_type_name}]"] = fields

        obj = Serializer.deserialize_one(self.model_class, http.get(url, params))
        if obj is None:
            raise UnmappedModelError(f"Cannot get resource {jsonapi_type_name} with id {resource_id}")
        return obj

    def get_one_related[RelModel: "Model"](
        self, resource_id: str, relationship_type: type[RelModel], relationship_name: str
    ) -> RelModel | None:
        jsonapi_type_name = self.model_class.jsonapi_type_name()
        url = urljoin(api_config.base_url, jsonapi_type_name, resource_id, "relationships", relationship_name)

        params = self._inclusion_params(relationship_name, relationship_type)
        return Serializer.deserialize_one(relationship_type, http.get(url, params))

    def __iter__(self) -> Iterator[TModel]:
        jsonapi_type_name = self.model_class.jsonapi_type_name()
        url = urljoin(api_config.base_url, jsonapi_type_name)
        params = {f"filter[{f.attribute}][{f.operator}]": f.value for f in self.filters}
        params["page[size]"] = str(self._page_size)
        fields = ",".join(self.model_class._jsonapi_attribute_names)
        if fields:
            params[f"fields[{jsonapi_type_name}]"] = fields

        if self.sorter:
            params["sort"] = self.sorter

        response = http.get(url, params)
        if response is None:
            return None
        yield from Serializer.deserialize_many(self.model_class, response)
        while (next_url := Serializer.deserialize_next_link(response)) is not None:
            response = http.get(urljoin(api_config.api_host, next_url))
            yield from Serializer.deserialize_many(self.model_class, response)

    def all(self) -> list[TModel]:
        return list(self)

    def firstn(self, n: int) -> list[TModel]:
        """Return the first n elements of the query as a list"""
        return list(islice(self, n))

    def first(self) -> TModel | None:
        """Return the first element of the query or None."""
        return next(iter(self), None)

    def ipick(self, *attributes: str) -> Iterable[tuple[Any, ...]]:
        # Primitive implementation using .__iter__().
        # Could be optimized by making requests that restrict fields to given attributes
        def make_tuple(o: TModel) -> tuple[Any, ...]:
            return tuple(getattr(o, attribute) for attribute in attributes)

        yield from (make_tuple(o) for o in self)

    def pick(self, *attributes: str) -> list[tuple[Any, ...]]:
        return list(self.ipick(*attributes))

    def iids(self) -> Iterable[str]:
        yield from (i[0] for i in self.ipick("id"))

    def ids(self) -> list[str]:
        return list(self.iids())

    def iter_many_related[RelModel: "Model"](
        self, resource_id: str, relationship_type: type[RelModel], relationship_name: str
    ) -> Iterable[RelModel]:
        url = urljoin(
            api_config.base_url, self.model_class.jsonapi_type_name(), resource_id, "relationships", relationship_name
        )
        params = self._inclusion_params(relationship_name, relationship_type)
        params["page[size]"] = str(self._page_size)
        response = http.get(url, params)
        if response is None:
            return None
        yield from Serializer.deserialize_many(relationship_type, response)
        while (next_url := Serializer.deserialize_next_link(response)) is not None:
            response = http.get(urljoin(api_config.api_host, next_url))
            yield from Serializer.deserialize_many(relationship_type, response)

    def where(self, attribute: str, operator: str, value: str | list[str]) -> "Request[TModel]":
        if isinstance(value, list):
            value = ",".join(value)

        if not isinstance(value, str):
            raise TypeError(f"value must be str or list, not {type(value)}")

        self.filters.append(Filter(attribute, operator, value))
        return self

    def asc(self, attribute: str) -> "Request[TModel]":
        if self.sorter is not None:
            raise IllegalSortError(f"Already sorted by `{self.sorter}`. Cannot sort by multiple attributes.")
        self.sorter = attribute
        return self

    def desc(self, attribute: str) -> "Request[TModel]":
        return self.asc("-" + attribute)

    def page_size(self, size: int) -> "Request[TModel]":
        if size < 1:
            raise ValueError("Page size must be at least 1")

        self._page_size = size
        return self

    def create(self, obj: TModel, meta: Meta = None):
        url = urljoin(api_config.base_url, self.model_class.jsonapi_type_name())
        response = http.post(url, json=Serializer.serialize_one(obj, meta, Action.CREATE))
        res = Serializer.deserialize_one(self.model_class, response)
        if res is not None:
            obj._jsonapi_attributes = res._jsonapi_attributes
            obj._id = res.id

    def update(self, obj: TModel, meta: Meta = None):
        if obj.id is None:
            raise UnmappedModelError("Model is unmapped and has no ID")
        url = urljoin(api_config.base_url, self.model_class.jsonapi_type_name(), obj.id)
        response = http.patch(url, json=Serializer.serialize_one(obj, meta, Action.UPDATE))
        res = Serializer.deserialize_one(self.model_class, response)
        if res is not None:
            obj._jsonapi_attributes = res._jsonapi_attributes
            obj._id = res.id

    def update_many_related(self, obj: TModel, relationship_name: str, *related: "Model"):
        if obj.id is None:
            raise UnmappedModelError("Model is unmapped and has no ID")
        url = urljoin(
            api_config.base_url, self.model_class.jsonapi_type_name(), obj.id, "relationships", relationship_name
        )
        http.post(url, json=Serializer.serialize_many_related(*related))

    def delete(self, obj: TModel, meta: Meta = None):
        if obj.id is None:
            raise UnmappedModelError("Model is unmapped and has no ID")
        url = urljoin(api_config.base_url, self.model_class.jsonapi_type_name(), obj.id)
        http.delete(url, Serializer.serialize_meta(meta))


class ModelMeta(type):
    __models__: ClassVar[dict[str, type]] = {}

    def __init__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]):
        super().__init__(name, bases, attrs)
        cls._jsonapi_attribute_names = [attr.api_attribute_name for attr in attrs.values() if type(attr) is Attribute]
        cls._model_attribute_names = [name for name, attr in attrs.items() if type(attr) is Attribute]
        ModelMeta.__models__[cls.__name__] = cls


class Model[TModel: "Model"](metaclass=ModelMeta):
    _model_attribute_names: ClassVar[list[str]]
    _jsonapi_attribute_names: ClassVar[list[str]]

    def __init__(self, **kwargs: str | int | list | dict | None):
        self._id = None
        if "id" in kwargs:
            self._id = str(kwargs["id"])
        kwargs.pop("id", None)
        kwargs.pop("type", None)
        self._jsonapi_attributes: dict[str, Any] = {}
        for arg, value in kwargs.items():
            if arg not in self._model_attribute_names:
                raise AttributeError(f"{type(self)} has no attribute {arg}")
            setattr(self, arg, value)
        self._jsonapi_to_many_relationships: dict[str, Iterable[TModel]] = {}
        self._jsonapi_to_one_relationships: dict[str, TModel] = {}

    @property
    def id(self) -> str | None:
        return self._id

    @classmethod
    def jsonapi_type_name(cls) -> str:
        return cls.__name__[0].lower() + cls.__name__[1:] + "s"

    @classmethod
    def get(cls, resource_id: str) -> Self:
        return Request(cls).get(resource_id)

    @classmethod
    def iter(cls) -> Iterable[Self]:
        return iter(Request(cls))

    @classmethod
    def first(cls) -> Self | None:
        return Request(cls).first()

    @classmethod
    def firstn(cls, n: int) -> Iterable[Self]:
        return Request(cls).firstn(n)

    @classmethod
    def where(cls, attribute: str, operator: str, value: str | list[str]) -> Request[Self]:
        return Request(cls).where(attribute, operator, value)

    @classmethod
    def asc(cls, attribute: str) -> Request[Self]:
        return Request(cls).asc(attribute)

    @classmethod
    def desc(cls, attribute: str) -> Request[Self]:
        return Request(cls).desc(attribute)

    def create(self, meta: Meta = None):
        Request(self.__class__).create(self, meta)

    def update(self, meta: Meta = None):
        Request(self.__class__).update(self, meta)

    def delete(self, meta: Meta = None):
        Request(self.__class__).delete(self, meta)

    def refresh(self):
        refreshed = self.get(self.id)
        self._jsonapi_attributes = refreshed._jsonapi_attributes
        self._id = refreshed._id

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Model)
            and self._id == other._id
            and self.jsonapi_type_name() == other.jsonapi_type_name()
            and all(getattr(self, name) == getattr(other, name) for name in self._model_attribute_names)
        )

    def __repr__(self) -> str:
        cutoff = 3

        attributes = ", ".join((f"{k!r}: {v!r}" for k, v in list(self._jsonapi_attributes.items())[:cutoff]))
        if len(self._jsonapi_attributes) > cutoff:
            attributes = attributes + ", ..."

        return f"<{type(self).__name__}(_id={self.id}, _json_api_attributes={{{attributes}}})>"
