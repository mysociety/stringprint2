# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'yaml'


Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "ubuntu/xenial64"

  # Enable NFS access to the disk
  config.vm.synced_folder ".", "/vagrant", :nfs => true

  # correct links to all the relevant directories
  config_yaml = YAML::load(File.read("#{File.dirname(__FILE__)}/conf/config.yaml"))
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
  config.vm.network "forwarded_port", guest: 8000, host: 8001
  #config.vm.network "forwarded_port", guest: 1080, host: 1080

  # Give the VM a bit more power to speed things up
  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 1
  end

  # Provision the vagrant box

  config.vm.provision "shell", path: "conf/provisioner.sh", privileged: false
  config.vm.provision "shell", inline: "touch /etc/is_vagrant_vm"
  config.vm.provision "shell", inline: <<-SHELL

    cd /vagrant

    #fix dpkg-preconfigure error
    export DEBIAN_FRONTEND=noninteractive
    # Install the packages from conf/packages
    xargs sudo apt-get install -qq -y < conf/packages

    # Run post-deploy actions script to update the virtualenv, install the
    # python packages we need, migrate the db and generate the sass etc
    conf/post_deploy_actions.bash
	conf/chrome_setup.bash
  SHELL


end
