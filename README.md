# Vilocify SDK and CLI tool

The Python SDK for [Vilocify](https://docs.vilocify.com), built using Vilocify's APIv2 JSON:API.
This project also includes an example CLI tool to manage Vilocify Monitoring Lists.

## Prerequisites
The Vilocify SDK needs Python 3.12 or newer.

## CLI usage
1. Get [pipx](https://pipx.pypa.io/stable/)
2. Install the CLI with `pipx install vilocify-sdk`
3. Run `vilocify --help` for documentation of the bundled example CLI tool

## SDK usage
The SDK is built on Vilocify's API.
We recommend you also take a quick look at the raw API docs at https://portal.vilocify.com/documentation.
In particular, study the "API resources" section and `filter[...][...]` parameters of main resources.
Those will come in handy for understanding the models of the SDK and arguments that can be used in `.where()` methods.

### Installation
Get `vilocify-sdk` from [PyPI](https://pypi.org/project/vilocify-sdk/).
If you use [Poetry](https://python-poetry.org/docs/) get it with `poetry add vilocify-sdk`.

### Authentication
You can generate an API Token at https://ui.portal.vilocify.com/api-tokens.

By default, authentication for the SDK is configured through the `VILOCIFY_API_TOKEN` environment variable.
Alternatively, the token can be set programmatically:
```python
from vilocify import api_config
api_config.token = "<your token here>"
```

### Examples

#### Inviting a new member into your org

Note that this code needs a token with "admin" role.
```python
from vilocify.models import Membership
m = Membership(username="John Doe", email="john.doe@example.com", role="user", expires_at="2025-10-30T00:00:00Z")
m.create()

print(m.invitation_state)
print(m.created_at)
```

#### Creating a monitoring list
```python
from vilocify.models import MonitoringList, Subscription, Component, Membership

# Creating a new monitoring list automatically adds the authenticated user as 'owner'
ml = MonitoringList(name="Example list", comment="created by the Vilocify SDK")
ml.components = [
    Component(id="40866"),
    Component(id="148860")
]
ml.create()

# Add a second subscriber to the list.
sub = Subscription(role="reader")
sub.monitoring_list = ml
sub.membership = Membership.where("email", "eq", "john.doe@example.com").first()
sub.create()

for subscription in ml.subscriptions:
    print(subscription.membership.email, "-", subscription.role)
```

#### Listing notifications for a monitoring list

```python
from vilocify.models import MonitoringList, Notification

ml = MonitoringList.where("name", "eq", "Example list").first()

# Find Vilocify notifications for the monitoring list since 2023
notifications = Notification.where("monitoringLists.id", "any", ml.id).where("createdAt", "after", "2023-01-01T00:00:00Z")
for n in notifications:
    print(n.title)
```

### Filtering
To filter models by supported attributes, use the `.where()` method, which takes three arguments.
The three arguments map 1-to-1 to `filter` parameters described in the [API Docs](https://portal.vilocify.com/documentation).

Take for example following request with a filter parameter from the docs:
```
GET /api/v2/notifications?filter[monitoringLists.id][any]=8c63252a-893e-4563-876b-a45ac9bdfff2
```
The corresponding Python code is
```python
Notification.where("monitoringLists.id", "any", "8c63252a-893e-4563-876b-a45ac9bdfff2")
```
The third parameter of `.where()` can either be a string or a list of strings.
Note that the SDK does not perform further validations which operators accept lists and which don't; lists simply get concatenated to comma-separated strings.
Check the API docs which filters support multiple values.

### Sorting
Sorting is handled by `.asc()` and `.desc()`.
Check the documentation of the `sort` parameter in top-level `GET /api/v2/{resources}` in the [API Docs](https://portal.vilocify.com/documentation) for available sorters.
The Vilocify API can only sort by a single attribute and does not support sorting by multiple attributes.
The SDK will raise an exception when attempting to sort an already sorted request.

### Relationships
The [models.py](vilocify/models.py) module defines the SDK models and their relationships, which closely reflects the "API Resources" drawing of the [API Docs](https://portal.vilocify.com/documentation).
Relationships cannot be set through the model constructor, but instead must be set using assignment. For example:

```python
sub = Subscription(role="user") # role is an attribute
sub.membership = Membership(id="<a_membership_id_here>")  # `.membership` is a to-one relation
sub.monitoring_list = MonitoringList(id="<a_ml_id_here>")  # `.monitoring_list` is a to-one relation
sub.create()  # Performs the API request to create the subscription


ml = MonitoringList(name="Example list") # name is an attribute
ml.components = [  # components is a to-many relationship
    Component(id="40866"),
    Component(id="148860")
]
ml.create()  # Creates a monitoring list with the two given components
```

#### Updating to-many relationships
The SDK provides two mechanisms to update to-many relationships.
One replaces all existing relationships and is not immediate, but needs a call to `.update()`.
The other extends the existing relationship and is immediate.
For example

```python
ml = MonitoringList.first()
ml.components = [  # Replaces all components on the monitoring list, no request is sent, yet.
    Component(id="1"),
    Component(id="2")
]
ml.update()  # Commit the change to the Vilocify API


ml = MonitoringList.first()
ml.components.extend(Component(id="3"), Component(id="5"))  # Adds component with IDs 1 and 2, and immediately sends the change to the API backend
```

### Proxy setup
The SDK uses a `requests.Session()` to handle its HTTP requests, which picks up the proxy settings from the `https_proxy` environment variable as documented [here](https://requests.readthedocs.io/en/latest/user/advanced/#proxies).
To override that behavior do the following:
```python
from vilocify import api_config
api_config.client.trust_env = False
api_config.client.proxies = { "https": "https://your.proxy:8080" }
```

## Contributing
See [Contributing.md](docs/CONTRIBUTING.md).

## License
[MIT License](LICENSE)

Copyright (c) 2025 Siemens AG
