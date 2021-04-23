#!/bin/bash
#$ -S /bin/bash
#$ -cwd
#$ -j y
#$ -o output.txt
#$ -M test@example.com
#$ -m be
#$ -P testPrj
#$ -pe shm 4
#$ -l h_rt=00:15:00
#$ -l h_vmem=4G
#$ -l m_mem_free=3G
#$ -l vendor=test
#$ -l gpu=2
#$ -t 10-100:5
#$ -q test.q


hello=HELLO

echo $TMP
echo $TMPDIR
echo $hello

echo $SGE_ACCOUNT
echo $SGE_ARCH
echo $SGE_BINARY_PATH
echo $SGE_BINDING
echo $SGE_CELL
echo $SGE_CWD_PATH
echo $SGE_JOB_SPOOL_DIR
echo $SGE_O_HOME
echo $SGE_O_HOST
echo $SGE_O_LOGNAME
echo $SGE_O_MAIL
echo $SGE_O_PATH
echo $SGE_O_SHELL
echo $SGE_O_WORKDIR
echo $SGE_ROOT
echo $SGE_STDERR_PATH
echo $SGE_STDIN_PATH
echo $SGE_STDOUT_PATH
echo $SGE_TASK_FIRST
echo $SGE_TASK_ID
echo $SGE_TASK_LAST
echo $SGE_TASK_STEPSIZE

