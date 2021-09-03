#!/usr/bin/env python3.6

import sys
import re

"""
Translates SGE batch script to Slurm

Derived from https://github.com/NIH-HPC/pbs2slurm/blob/master/pbs2slurm.py

The SGE script is split into 
- a shebang line
- a header containing all the SGE options denoted by #$
- the commands the script actually executes

The script then:
- Outputs the shebang line. If no shebang line was detected a default
  of #!/bin/bash is added.
- Translates #$ directives into their #SBATCH counterparts when 
  applicable. Note that not all options are handled in this script.
  For a full list of SBATCH directives see the Slurm documentation at:
  https://slurm.schedmd.com/sbatch.html
- Translates common SGE environment variables into their Slurm 
  counterparts

If no input file is provided, sge2slurm will read from stdin.

All output is sent directly to stdout i.e the console. sge2slurm should
not overwrite the script unless directed by the user.

Please be sure to manually go over translated scripts and make any 
neccesary corrections.

Examples:
    sge2slurm sge_script
    sge2slurm < sge_script > slurm_script
    sge2slurm sge_script > slurm_script
    sge2slurm -s /bin/zsh sge_script > slurm_script

"""
__version__ = 1.0
__author__ = "Cameron Fritz"

def info(s):
    print("INFO:    {}".format(s), file=sys.stderr)
def warn(s):
    print("WARNING: {}".format(s), file=sys.stderr)
def error(s):
    print("ERROR:   {}".format(s), file=sys.stderr)

def seperate_script(input):
    """Separates script into the shebang, sge options, and all other command lines"""
    lines = input.split("\n")
    n = len(lines)
    i = 0
    if lines[0].startswith("#!"):
        shebang = lines[0]
        i = 1
    else:
        shebang = None
    sge_options = []
    while True:
        if i == n:
            error("reached end of the file without finding any commands")
            sys.exit(1)
        if lines[i].startswith("#") or lines[i].strip() == "":
            sge_options.append(lines[i])
            i += 1
        else:
            break
    if not sge_options:
        return shebang, "", "\n".join(lines[i:])
    else:
        if len([x for x in sge_options if x.startswith("#$")]) > 0:
            return shebang, "\n".join(sge_options), "\n".join(lines[i:])
        else:
            return shebang, "", "\n".join(sge_options + lines[i:])

def fix_commands(commands):
    """Translate SGE environment variables into their Slurm counterparts"""
    repl = {
        "SGE_O_WORKDIR" : "SLURM_SUBMIT_DIR", #General variable changes
        "JOB_ID" : "SLURM_JOB_ID",
        "JOB_NAME": "SLURM_JOB_NAME",
        "NHOSTS" : "SLURM_JOB_NUM_NODES",
        "NSLOTS" : "SLURM_NTASKS",
        "SGE_TASK_ID" : "SLURM_ARRAY_TASK_ID", #Array variable changes
        "SGE_TASK_FIRST" : "SLURM_ARRAY_TASK_MIN",
        "SGE_TASK_LAST" : "SLURM_ARRAY_TASK_MAX",
        "SGE_TASK_STEPSIZE" : "SLURM_ARRAY_TASK_STEP" }
    output = commands
    for sge, slurm in repl.items():
        output = output.replace(sge, slurm)
    return output

def fix_directory(sge_options):
    """Removes #$ -cwd as it is no longer necessary"""
    directory_re = re.compile(r'#\$ -cwd')
    def _repl(m):
         info("#$ -cwd is a default in Slurm")
         return ""
    return directory_re.sub(_repl, sge_options)

def fix_shell(sge_options):
    """Removes #$ -S as it is no longer necessary"""
    shell_re = re.compile(r'^#\$[ \t]*-S[ \t]*(\S*)[^\n]*', re.M)
    def _repl(m):
        info("#$ -S: slurm uses #! (shebang) to determine shell")
        return ""
    return shell_re.sub(_repl, sge_options)

def fix_email_address(sge_options):
    """Translate #$ -M into #SBATCH --mail-user"""
    address_re = re.compile(r'^#\$[ \t]*-M[ \t]*\b(.*)\b[^\n]*', re.M)
    match = address_re.search(sge_options)
    
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -M without argument")
            return ""
        
        addresses = [x.strip() for x in m.group(1).split(",")]
        valid_addresses = []

        for adr in addresses:
            if re.match(r'[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,4}', adr) is not None:
                valid_addresses.append(adr)
        
        if not(valid_addresses):
            warn("email address may be invalid: '{}'".format(addresses[0]))
            address = addresses[0]
        else:
            address = valid_addresses[0]
        return '#SBATCH --mail-user={}'.format(address)
    
    return address_re.sub(_repl, sge_options)

def fix_email_notifications(sge_options):
    """Translate #$ -m into #SBATCH --mail-type
    Note: Does not handle (s)uspend event as
          Slurm has no corresponding option"""
    notification_re = re.compile(r'^#\$[ \t]*-m[ \t]*([aben]{0,4})[^\n]*', re.M)
    def _repl(m):
        events = m.group(1)
        if events == "" or "n" in events:
            return ""
        
        slurm_events = []
        if "b" in events:
            slurm_events.append("BEGIN")
        if "e" in events:
            slurm_events.append("END")
        if "a" in events:
            slurm_events.append("FAIL")
        
        slurm_events.sort()
        return "#SBATCH --mail-type={}".format(",".join(slurm_events))

    return notification_re.sub(_repl, sge_options)

def fix_account(sge_options):
    """Translates #$ -P into #SBATCH -A"""
    account_re = re.compile(r'^#\$[ \t]*-P[ \t]*(\S*)[^\n]*', re.M)
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -P without argument")
            return ""
        else:
            if re.search('Prj', m.group(1)) != None:
                account = m.group(1).replace("Prj", "Grp")
            else:
                account = m.group(1)
            return '#SBATCH -A {}'.format(account)
    return account_re.sub(_repl, sge_options)

def fix_resources(sge_options):
    """Translates #$ -l into #SBATCH directives
    NOTE: Not all possible resource requests handled.
          Memory in SGE is based on slots while memory
          in Slurm is based on Nodes. Memory value will
          lower than expected."""
    resource_re = re.compile(r'^#\$[ \t]*-l[ \t]*(\S*)[^\n]*', re.M)
    match = resource_re.search(sge_options)
    mem_re = re.compile(r'm_mem_free=(\d+)(\w+)')
    h_rt_re = re.compile(r'h_rt=(\d+):(\d+):(\d+)')
    only_seconds_re = re.compile(r'h_rt=(\d+)')
    gpu_re = re.compile(r'gpu=(\d)')

    if match is not None:
        def _repl(m):
            new_resources = []
            resources = m.group(1)
            
            # Handle memory, note memory is handled differently in SGE than Slurm
            if "m_mem_free" in resources:
                mem_m = mem_re.search(resources)
                if mem_m is not None:
                    warn("Memory in SGE is per slot. Memory in Slurm is per node. Adjust accordingly")
                    memory = mem_m.group(1)
                    size = mem_m.group(2)
                    new_resources.append("#SBATCH --mem={}{}".format(memory, size))
            
            # Handle hard runtime limit, handles hh:mm:ss and only seconds (ss)
            if "h_rt" in resources:
                h_rt_m = h_rt_re.search(resources)
                only_seconds_m = only_seconds_re.search(resources)
                if h_rt_m is not None:
                    h = h_rt_m.group(1)
                    m = h_rt_m.group(2)
                    if len(m) == 1:
                        m += "0"
                        s = h_rt_m.group(3)
                        if len(s) == 1:
                            s += "0"
                            new_resources.append("#SBATCH -t={}:{}:{}".format(h, m, s))
                        elif len(s) > 2:
                            error("Improper value in the seconds field")
                    elif len(m) > 2:
                        error("Improper value in the minutes field")
                elif only_seconds_m is not None:
                    time = int(only_seconds_m.group(1))
                    s = time % 60
                    time = time // 60
                    m = time % 60
                    h = time // 60
                    new_resources.append("#SBATCH -t={}:{}:{}".format(h, m, s))
            
            # Handle gpu requests
            if "gpu" in resources:
                gpu_m = gpu_re.search(resources)
                if gpu_m == None:
                    info("$SBATCH --gpus can be modified to request type of gpu")
                    new_resources.append("#SBATCH --gres=gpus:{}".format(gpu_m.group(1)))

            return "\n".join(new_resources)
        sge_options = resource_re.sub(_repl, sge_options)
    return sge_options

def fix_slots(sge_options):
    """Translates #$ -pe into #SBATCH -N and #SBATCH --ntasks-per-node
    NOTE: Only handles fixed and shm PEs. 
          For all other PEs will default to: 
          #SBATCH -N 1
          #SBATCH --ntasks-per-node 16"""
    pe_re = re.compile(r'#\$[ \t]*-pe[ \t]*(\S*)[ \t](\d+)[^\n]*')
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -pe has no argument")
            return ""
        elif m.group(1) == "shm":
            total_slots = m.group(2)
            try:
                total_slots = int(total_slots)
                warn("Assumption of max 16 slots per node. Make corrections as necessary")
                if total_slots <= 16:
                    return "#SBATCH -N 1\n#SBATCH --ntasks-per-node {}\n".format(total_slots)
                else:
                    nodes = total_slots // 16
                    return "#SBATCH -N {}\n#SBATCH --ntasks-per-node {}\n".format(nodes, 16)
            except ValueError:
                error("Invalid value for pe slots. Slots must be an integer")
                return ""
        elif m.group(1).startswith("fixed"):
            fixed_num = m.group(1)[5:]
            total_slots = m.group(2)
            try:
                fixed_num = int(fixed_num)
                total_slots = int(total_slots)
                num_nodes = total_slots // fixed_num
                return "#SBATCH -N {}\n#SBATCH --ntasks-per-node {}\n".format(num_nodes, fixed_num)
            except ValueError:
                error("Invalid value for pe slots. Slots must be an integer")
                return ""
        else:
            warn("Only fixed and shm PEs are handled in this script. Please make corrections yourself. Defaulting to 1 node with 16 slots.")
            return "#SBATCH -N 1\n#SBATCH --ntasks-per-node 16\n"
    return pe_re.sub(_repl, sge_options)

def fix_restart(sge_options):
    """Translates #$ -r into #SBATCH --requeue"""
    restart_re = re.compile(r'^#\$[ \t]*-r[ \t]*(\S*)[^\n]*', re.M)
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -r with no argument")
            return ""
        elif "y" == m.group(1):
            return "#SBATCH --requeue"
        elif "n" == m.group(1):
            return "#SBATCH --no-requeue"
        else:
            return ""
    return restart_re.sub(_repl, sge_options)

def fix_output_stream(sge_options):
    """Translates #$ -o, #$ -e, #$ -j into #SBATCH -o and #SBATCH -e
    NOTE: Slurm output streams are joined by default."""
    out_re = re.compile(r'^#\$[ \t]*-o[ \t]*(\S*)[^\n]*', re.M)
    err_re = re.compile(r'^#\$[ \t]*-e[ \t]*(\S*)[^\n]*', re.M)
    join_re = re.compile(r'^#\$[ \t]*-j[ \t]*(\S{0,4})[^\n]*', re.M)

    # Remove the -j directive
    def _repl(m):
        info("#$ -j is the default in Slurm")
        return ""
    sge_options = join_re.sub(_repl, sge_options)
    
    # Fix the -o directive
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -o with no argument")
            return ""
        else:
            return "#SBATCH -o {}".format(m.group(1))
    sge_options = out_re.sub(_repl, sge_options)
    
    # Fix the -e directive
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -e with no argument")
            return ""
        else:
            return "#SBATCH -e {}".format(m.group(1))
    sge_options = err_re.sub(_repl, sge_options)
    
    return sge_options

def fix_partition(sge_options):
    """Translates #$ -q into #SBATCH -p"""
    partition_re = re.compile(r'#\$[ \t]*-q[ \t]*(\S*)[^\n]*')
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -q with no argument")
            return ""
        else:
            info("Partition names in Slurm may be different than queue names in SGE")
            return "#SBATCH -p {}".format(m.group(1))
        return
    return partition_re.sub(_repl, sge_options)

def fix_array(sge_options):
    """Translates #$ -t into #SBATCH --array"""
    array_re = re.compile(r'^#\$[ \t]*-t[ \t]*([-:0-9]*)[^\n]*', re.M)
    
    def _repl(m):
        if m.group(1) == "":
            warn("#$ -t with no argument")
            return ""
        else:
            return "#SBATCH --array={}".format(m.group(1))
    return array_re.sub(_repl, sge_options)

def convert_script(script, interpreter="/bin/bash"):
    """Main Conversion Function, calls all other functions necessary to convert script."""
    shebang, sge_options, commands = seperate_script(script)

    if shebang is None:
        shebang = "#! {}".format(interpreter)
    commands = fix_commands(commands)
    if sge_options != "":
        sge_options = fix_directory(sge_options)
        sge_options = fix_shell(sge_options)
        sge_options = fix_email_address(sge_options)
        sge_options = fix_email_notifications(sge_options)
        sge_options = fix_account(sge_options)
        sge_options = fix_resources(sge_options)
        sge_options = fix_slots(sge_options)
        sge_options = fix_restart(sge_options)
        sge_options = fix_output_stream(sge_options)
        sge_options = fix_partition(sge_options)
        sge_options = fix_array(sge_options)
        return "{}\n{}\n{}".format(shebang, sge_options, commands)
    else:
        return "{}\{}".format(shebang, commands)
   
if __name__ == "__main__":
    import argparse
    
    cmdline = argparse.ArgumentParser(description = __doc__, formatter_class = argparse.RawDescriptionHelpFormatter)
    cmdline.add_argument("--shell", "-s", default ="/bin/bash")
    cmdline.add_argument("--version", "-v", action = "store_true", default = False)
    cmdline.add_argument("sge_script", type = argparse.FileType('r'), nargs = "?", default = sys.stdin)
    
    args = cmdline.parse_args()

    if args.version:
        print("sge2slurm V{}".format(__version__))
        sys.exit(0)
    if args.sge_script.isatty():
        print("Please provide a SGE bash script either on stdin or as an argument", file = sys.stderr)
        sys.exit(1)

    slurm_script = convert_script(args.sge_script.read(), args.shell)
    print(slurm_script)
