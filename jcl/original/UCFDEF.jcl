//UCFDEF   JOB (ACCT),'DEFINE UCF BASE',CLASS=A,MSGCLASS=A,
//             NOTIFY=&SYSUID
//STEP1    EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  DEFINE CLUSTER (NAME(UCF.BASE)            -
         NONINDEXED                              -
         RECORDSIZE(469 469)                     -
         VOLUMES(UCF001)                          -
         CYLINDERS(400 100)                       -
         FREESPACE(0 0)                           -
         SHAREOPTIONS(2 3)                        -
         SPEED)                                   -
    DATA (NAME(UCF.BASE.DATA))
/*
