# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'yaml'

config_yaml = YAML::load(File.read("#{File.dirname(__FILE__)}/proj/conf/config.yaml"))

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
    config.vm.synced_folder value["storage_dir"], storage_dir
    config.vm.synced_folder value["publish_dir"], publish_dir
  end

  # Speed up DNS lookups
  config.vm.provider "virtualbox" do |vb|
    vb.customize ["modifyvm", :id, "--natdnsproxy1", "off"]
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "off"]
  end

  # Use a host-only network
  # This also allows you to test via other devices (e.g. mobiles) on the same
  # network, or use NFS if you prefer.
  config.vm.network :private_network, ip: "10.11.12.13"

  # Django dev server
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  # Give the VM a bit more power to speed things up
  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 1
  end

  # Provision the vagrant box

  config.vm.provision "shell", path: "#{File.dirname(__FILE__)}/script/vagrant-provision"
  
  # activate venv on ssh start
  config.vm.provision "shell", inline: 'echo ". /vagrant/venv/bin/activate" > ~/.profile', privileged: false

end
