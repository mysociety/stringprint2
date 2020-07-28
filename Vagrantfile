load 'vagrant_base.rb'

Vagrant.configure(2) do |config|
  config.vm.synced_folder ".", "/vagrant/stringprint"
  config.ssh.extra_args = ["-t", "cd /vagrant/stringprint; bash --login"]
end

