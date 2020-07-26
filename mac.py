import platform, os
def cpu_info():
    if platform.system() == 'Windows':
        return platform.processor()
    elif platform.system() == 'Darwin':
        command = '/usr/sbin/sysctl -n machdep.cpu.brand_string'
        return os.popen(command).read().strip()
    elif platform.system() == 'Linux':
        command = 'cat /proc/cpuinfo'
        return os.popen(command).read().strip()
    return 'platform not identified'
# print(cpu_info())

print(platform.version)

print(platform.machine())

print(platform.version())

print(platform.platform())

print(platform.uname())

print(platform.uname().node)

print(platform.system())

print(platform.processor())
