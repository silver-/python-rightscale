import datetime
from XMLModel import XMLModel
from util import ElementTreeValueOK
from Tag import Tag
from Tags import Tags
from ServerSettings import ServerSettings
from ServerTemplate import ServerTemplate
from Status import Status

# TODO(sissel): Refactor
import xml.etree.ElementTree as ElementTree
XMLCLASS = ElementTree.XML("<a />").__class__

class ExecutionError(Exception):
    pass

class Server(XMLModel):
  _nickname = None
  _href = None
  _state = None
  _updated_at = None
  _created_at = None
  _server_type = None
  _current_instance_href = None
  _tags = list()

  _server_template = None
  _server_template_href = None

  _deployment = None
  _deployment_href = None

  # ServerSettings
  _settings = None

  def __str__(self):
    return "%s" % (self.nickname)

  @property
  def href(self):
    """ The href for this server """
    return self._href

  @href.setter
  @ElementTreeValueOK
  def href(self, value):
    self._href = value

  @property
  def settings(self):
    """ The settings for this server, returns a ServerSettings object
        See also: 'sub-resources' on this API reference:
          http://support.rightscale.com/15-References/RightScale_API_Reference_Guide/02-Management/02-Servers"""
    if self._settings is None:
      self._settings = ServerSettings("%s/settings" % self._href, self.rsapi)
    return self._settings

  @settings.setter
  @ElementTreeValueOK
  def settings(self, value):
    self._settings = ServerSettings(value, self.rsapi)

  @property
  def server_template(self):
    """ The ServerTemplate for this server. """
    if self._server_template is None:
      self.get_server_template
    return self._server_template

  def get_server_template(self):
    self._server_template = ServerTemplate(self.server_template_href, self.rsapi)
  # def get_server_template

  @server_template.setter
  @ElementTreeValueOK
  def server_template(self, value):
    # Defer loading ServerTemplate until it is requested.
    self._server_template_href = value

  @property
  def current_instance_href(self):
    """ The current instance href. """
    return self._current_instance_href

  @current_instance_href.setter
  @ElementTreeValueOK
  def current_instance_href(self, value):
    self._current_instance_href = value

  @property
  def deployment_href(self):
    """ The deployment href """
    return self._deployment_href

  @deployment_href.setter
  @ElementTreeValueOK
  def deployment_href(self, value):
    self._deployment_href = value

  @property
  def deployment(self):
    """ The Deployment object for this server """
    assert self._deployment_href
    from Deployment import Deployment
    return Deployment(self._deployment_href, self.rsapi)

  @property
  def nickname(self):
    """ The server nickname according to RightScale. Displayed in the UI. """
    return self._nickname

  @nickname.setter
  @ElementTreeValueOK
  def nickname(self, value):
    self.taint("nickname")
    self._nickname = value

  @property
  def state(self):
    """ The server state (pending/booting/operational). """
    return self._state

  @state.setter
  @ElementTreeValueOK
  def state(self, value):
    self._state = value

  @property
  def updated_at(self):
    """ `datetime.datetime` of last server update. """
    return self._updated_at

  @updated_at.setter
  @ElementTreeValueOK
  def updated_at(self, value):
    self._updated_at = self._parse_datetime(value)

  @property
  def created_at(self):
    """ `datetime.datetime` of server creation. """
    return self._created_at

  @created_at.setter
  @ElementTreeValueOK
  def created_at(self, value):
    self._created_at = self._parse_datetime(value)

  @property
  def server_type(self):
    """ Server type (e.g. "ec2"). """
    return self._server_type

  @server_type.setter
  @ElementTreeValueOK
  def server_type(self, value):
    self._server_type = value

  @property
  def tags(self):
    """ The tags for this server. """
    if not self._tags:
      self._tags = Tags(rsapi=self.rsapi)
      # Use current_instance_href if it is present, otherwise
      # use the normal server href.
      if self.current_instance_href:
        self._tags.for_resource(self.current_instance_href)
      else:
        self._tags.for_resource(self.href)
    #self._tags = current_tags
    return self._tags

  @tags.setter
  def tags(self, value):
    self.taint("tags")
    #print "Setting tags for %s to %s" % (self, value)
    if isinstance(value, XMLCLASS) and value.tag == "tags":
      self._tags = list()
      for element in value:
        self.tags.append(Tag(element, self.rsapi))
      # for element ...
    else:
      self._tags = value
  # def tags

  def run_script(self, script_id, script_inputs=None):
    """ Runs script on this Server.
        
        Inputs to the script may be passed in ``script_inputs`` dictionary.
    """
    # Build script href
    script_href = "https://my.rightscale.com/api/acct/%s/right_scripts/%s" % \
                  (self.rsapi.account, script_id)
    params = {'server[right_script_href]': script_href}

    # Prepare script inputs
    script_inputs = script_inputs or {}
    for param, value in script_inputs.items():
        key = 'server[parameters][%s]' % param
        params[key] = 'text:%s' % value

    # Run script
    href = self.href + "/run_script"
    response, content = self.rsapi.request(href, body=params, method="POST")
    if 'location' not in response:
        raise ExecutionError(content)
    return Status(response.get('location'), self.rsapi)

  def save(self):
    """ Save any modifications made to this Server.

        Can save:
          - tags
          - nickname

        Saving tags will affect the current instance as well as the 'next'
        instance.
        """
    if "tags" in self.tainted:
      self.rsapi.save_tags(self, self.tags)
      self.untaint("tags")

    if len(self.tainted) > 0:
      #print "Want to save: %s" % (",".join(self.tainted.keys()))
      params = { }
      if "nickname" in self.tainted:
        params["server[nickname]"] = self.nickname
        self.untaint("nickname")
      # add other features here...

      response, content = self.rsapi.request(self.href, params, method="PUT")
      if response["status"] != "204":
        raise InvalidResponse("Error while updating server %s: (code %s) %s" 
            % (self.href, response["status"], content))
      else:
        assert len(content) == 0, "RightScale API docs claim content from a server update request will be empty"
      # for url in ...
    # if len(self.tainted) > 0
  # def save

  def _parse_datetime(self, datetime_str):
    """ Return `datetime.datetime` object, parsed from string in
        RightScale date/time format. """
    return datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")


  ELEMENTS = {
    "current-instance-href": current_instance_href, 
    "href": href, 
    "nickname": nickname, 
    "server-template-href": server_template,
    "settings": settings, 
    "deployment-href": deployment_href,
    "state": state,
    "updated-at": updated_at,
    "created-at": created_at,
    "server-type": server_type,

    # Ignore the 'tags' data as this data is for the 'next' server version,
    # not the current instance.
    "tags": None
  }
# class Server
