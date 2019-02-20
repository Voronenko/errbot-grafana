import requests
import json
from jinja2 import Template
import urllib.request
import re

class GrafanaHelper(object):

    def __init__(self, grafana_server_address, grafana_token):
        self.grafana_token = grafana_token
        self.grafana_server_address = grafana_server_address

    def get_dashboards(self, tag=None):
        if tag is not None:
            result = self.call_grafana(
                "search?type=dash-db&tag={0}".format(tag))
        else:
            result = self.call_grafana("search?type=dash-db")
        return result

    def get_dashboard_details(self, slug):
        dashboard = self.call_grafana("dashboards/db/{0}".format(slug))
        data = dashboard["dashboard"]
        panels = []
        if ("rows" not in data) or len(data["rows"]) == 0:
            if len(data["panels"]) == 0:
                return "Dashboard empty"
            else:
                data["rows"] = [{"panels": data["panels"]}]
        if len(data["templating"]["list"]) > 0:
            template_map = {}
            for template in data["templating"]["list"]:
                if "current" not in template:
                    continue
                if "text" in template["current"]:
                    template_map["$" + template["name"]] = template["current"][
                        "text"]
                else:
                    template_map["$" + template["name"]] = ""
        panel_number = 0
        for row in data["rows"]:
            for panel in row["panels"]:
                panel["panel_number"] = panel_number
                panel_number += 1
                panels.append(panel)
        data["allpanels"] = panels
        return data

    def search_dashboards(self, query):
        result = self.call_grafana(
            "search?type=dash-db&query={0}".format(query))
        return result

    def render_raw(self, mess):
        regex = "(?:!grafana) (?:render) ([A-Za-z0-9\-\:_]+)(.*)?"
        matches = re.findall(regex, mess)[0]
        slug = matches[0].strip()
        tuning_params = matches[1].strip()
        return self.render(slug, tuning_params)

    def render(self, slug, tuning_params="", period_from=None, period_to=None):

        timespan = {
            "from": period_from or "now-6h",
            "to": period_to or "now"
        }
        apiEndpoint = 'dashboard-solo'
        variables = ''
        template_params = []
        visual_panel_id = False
        apiPanelId = False
        visual_panel_name = False
        imagesize = {
            "width": 1000,
            "height": 500
        }
        variables = ""

        # Check if we have any extra fields
        if tuning_params and tuning_params != '':
            # The order we apply non-variables in
            timeFields = ['from', 'to']

            for part in tuning_params.split():
                name, value = part.split('=')
                variables = "{0}&var-{1}".format(variables, part)
                template_params.append({"name": name, "value": value})

        parts = slug.split(":")
        if len(parts) > 1:
            slug = parts[0]
            if parts[1].isdigit():
                visual_panel_id = int(parts[1])
            else:
                visual_panel_name = parts[1].lower()

        data = self.get_dashboard_details(slug)
        if ("rows" not in data) or len(data["rows"]) == 0:
            if len(data["panels"]) == 0:
                return "Dashboard empty"
            else:
                data["rows"] = [{"panels": data["panels"]}]
        if len(data["templating"]["list"]) > 0:
            template_map = {}
            for template in data["templating"]["list"]:
                if "current" not in template:
                    continue
                for _param in template_params:
                    if template["name"] == _param["name"]:
                        template_map["$" + template["name"]] = _param["value"]
                    else:
                        if len(template["current"]) > 0:
                            template_map[
                                "$" + template.name] = template["current"][
                                "text"]

        panel_number = 0
        for row in data["rows"]:
            for panel in row["panels"]:
                panel_number += 1
                # Skip if visual panel ID was specified and didn't match
                if visual_panel_id and visual_panel_id != panel["id"]:
                    continue
                # Skip if API panel ID was specified and didn't match
                if apiPanelId and apiPanelId != panel["id"]:
                    continue

                if visual_panel_name and panel["title"].lower().find(
                    visual_panel_name) == -1:
                    continue

                title = panel["title"]
                #            imageUrl = "#{grafana_host}/render/#{apiEndpoint}/db/#{slug}/
                # ?panelId=#{panel.id}&width=#{imagesize.width}&height=#{imagesize.height}
                # &from=#{timespan.from}&to=#{timespan.to}#{variables}"
                imageUrl = "{0}/render/{1}/db/{2}/?panelId={3}&width={4}&height={5}&from={6}&to={7}{8}".format(
                    self.grafana_server_address,
                    apiEndpoint,
                    slug,
                    panel["id"],
                    imagesize["width"],
                    imagesize["height"],
                    timespan["from"],
                    timespan["to"],
                    variables
                )

                link = "{0}/dashboard/db/{1}/?panelId={2}&width={3}&height={4}&from={5}&to={6}{7}".format(
                    self.grafana_server_address,
                    slug,
                    panel["id"],
                    imagesize["width"],
                    imagesize["height"],
                    timespan["from"],
                    timespan["to"],
                    variables
                )

                return {
                    "title": title,
                    "imageUrl": imageUrl,
                    "link": link,
                    "template_params": template_params,
                    "timespan": timespan
                }
        return {}

    def pretty_dashboards(self, response):
        with open('templates/grafana_dashboards_list.md') as file_:
            template = Template(file_.read())
            rendered = template.render(dashboards=response)
            return rendered

    def call_grafana(self, url):
        """

        :type url: basestring
        """
        target_url = "{0}/api/{1}".format(self.grafana_server_address, url)
        r = requests.get(target_url, headers=self.grafana_headers(False))
        result = json.loads(r.content)
        return result

    def post_grafana(self, url, data):
        target_url = "{0}/api/{1}".format(self.grafana_server_address, url)
        r = requests.post(target_url, data=json.dumps(data),
                          headers=self.grafana_headers(True))
        result = json.loads(r.content)
        return result

    def get_grafana_image(self, url):
        opener = urllib.request.build_opener()
        opener.addheaders = [
            ("Authorization", "Bearer {0}".format(self.grafana_token))
        ]
        urllib.request.install_opener(opener)
        #        fd, path = tempfile.mkstemp()
        path, headers = urllib.request.urlretrieve(url)
        return {
            "path": path,
            "headers": headers
        }

    def grafana_headers(self, post=False):
        headers = {"Accept": "application/json",
                   "Authorization": "Bearer {0}".format(self.grafana_token)
                   }
        if post:
            headers["Content-Type"] = "application/json"
        return headers
