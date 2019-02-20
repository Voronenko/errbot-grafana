**id**  **slug**       **title**        *comma separated tags*

{{ dashboard["id"] }} {{ slug }} {{ dashboard["title"] }} {% for tag in dashboard.tags %}*{{ tag }}*{% if not loop.last %},{% endif %}{% endfor %}

Possible params

> name  label
{% for param in dashboard["templating"]["list"] %}
> **{{param["name"]}}** _{{param["label"]}}_
{% endfor %}


Panels

**number**     "title"
{% for panel in dashboard["allpanels"] %}
**{{ panel["id"] }}**   "{{panel["title"]}}"

_!grafana render --from=now-6h --to=now {{ slug }}:{{panel["id"] }}_ "PARAM1=VALUE1 PARAM2=VALUE2"

_!grafana render  --from=now-6h --to=now {{ slug }}:TITLEQUERY_ "PARAM1=VALUE1 PARAM2=VALUE2" 
{% endfor %}
