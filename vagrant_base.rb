# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'yaml'

config_yaml = YAML::load(File.read("#{File.dirname(__FILE__)}/proj/conf/config.yaml"))

def is_env_format(v)
	if v.class == String
		return v.slice(0,2) == "%%"
	else
		return false
	end
end

def fix_format(v)
	v.slice(2..-3)
end

#get variables that are environmental variables
def get_env_vars(yml)
	env_vars = Array.new
	yml.each do |key, value|
		if value.class == Hash
			env_vars += get_env_vars(value)
		else
			if is_env_format(value)
				env_vars << fix_format(value)
			end
		end
	end
	return env_vars
end

env_vars = get_env_vars(config_yaml)
commands = Array.new

#add line pulling in environmental variables
env_vars.each do |e|
	env_var_cmd = ""
	if ENV[e]
		value = ENV[e]
		env_var_cmd = <<CMD
echo "export #{e}=#{value}" | tee -a /home/vagrant/.profile
CMD
	end
	commands.push(env_var_cmd)
end

script = commands.join("")


Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "ubuntu/xenial64"


  # connect links to all the relevant directories
  config_yaml["ORGS"].each do |key, value|
	storage_dir = "/sp_" + key + "_storage"
	publish_dir = "/sp_" + key + "_publish"
	config.vm.synced_folder value["storage_dir"], storage_dir, :nfs => true
	config.vm.synced_folder value["publish_dir"], publish_dir, :nfs => true
  end

  # Speed up DNS lookups
  config.vm.provider "virtualbox" do |vb|
    vb.customize ["modifyvm", :id, "--natdnsproxy1", "off"]
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "off"]
  end

  # NFS requires a host-only network
  # This also allows you to test via other devices (e.g. mobiles) on the same
  # network
  config.vm.network :private_network, ip: "10.11.12.13"

  # Django dev server
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  # Give the VM a bit more power to speed things up
  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 1
  end

  # Provision the vagrant box

  config.vm.provision "shell", :inline => script
  config.vm.provision "shell", path: "script/vagrant-provision"
  
  # activate venv on ssh start
  config.vm.provision "shell", inline: 'echo ". /vagrant/venv/bin/activate" > ~/.profile', privileged: false

end
