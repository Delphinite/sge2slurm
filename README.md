# Translating batch scripts with #$ directives into Slurm Scripts with #SBATCH directives
`sge2slurm.py` translates SGE batch scripts into Slurm batch scripts. It translates some, but not all directives, and a limited subset of environmental variables.

## Usage
```
  usage: sge2slurm [-h] [--shell SHELL] [--version] [sge_script]
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
  
  Positional arguments:
    sge_script

  Optional arguments:
    -h, --help            show this help message and exit
    --shell SHELL, -s SHELL
                          Shell to insert if shebang line (#! ...) is missing.
                          Defaults to '/bin/bash'
    --version, -v
```

## sge2slurm notes
* SGE directives in batch script use a more relaxed grammar than command line switches. For example all of the following will be correctly translated:
  * #$ -o foo
  * #$ -ofoo
  * #$-ofoo

* This script does not handle every possible option just ones that I have personally encountered. 

* This script does not take time to deal with the same option appearing multiple times. It will generally translate them all regardless. 

* This script is not a universal fix and cannot account for every possible installation. Make changes based on your specific installation of Slurm.
