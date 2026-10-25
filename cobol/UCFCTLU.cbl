       IDENTIFICATION DIVISION.
       PROGRAM-ID. UCFCTLU.
      *----------------------------------------------------------*
      * UCFCTLU: STAMP A BUILD RECORD IN HLQ.UCF.CTL (BATCH).    *
      *   PARM='RECID,DATASET.NAME'                              *
      *   E.G. PARM='SNDXSTAT,UCF.PROD.OWNER.SNDXLKP'            *
      * WRITES OR REWRITES THE RECORD WITH TODAY'S DATE/TIME:    *
      *   CT-REC-ID        RECID (8)                             *
      *   CT-LAST-CLAIM-ID ZEROS (USED ONLY BY CLAIMNO)          *
      *   CT-LAST-UPD-DATE YYYYMMDD                              *
      *   CT-LAST-UPD-USER 'BATCH'                               *
      *   CT-DATA          DSN X(44) DATE 9(8) TIME 9(6) X(8)    *
      * RECORD IDS USED: LOADSTAT (OWNER LOAD), HOLDSTAT, ZIPSTAT,*
      * SNDXSTAT (LOOKUP BUILDS), NUMISTAT (NUMIDENT LOAD).      *
      * CLAIMNO IS NEVER TOUCHED HERE.                           *
      * THE CICS FILE MUST BE CLOSED WHILE THIS RUNS.            *
      * RETURN CODE 0 OK, 8 BAD PARM, 12 FILE ERROR.             *
      *----------------------------------------------------------*
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CTL-FILE ASSIGN TO UCFCTL
               ORGANIZATION IS INDEXED
               ACCESS MODE IS RANDOM
               RECORD KEY IS CT-REC-ID
               FILE STATUS IS WS-FS.
       DATA DIVISION.
       FILE SECTION.
       FD  CTL-FILE.
           COPY UCFCTL.
       WORKING-STORAGE SECTION.
       01  WS-FS                   PIC XX.
       01  WS-RECID                PIC X(8).
       01  WS-DSN                  PIC X(44).
       01  WS-NOW                  PIC X(21).
       01  WS-STAT-DATA.
           05  WS-STAT-DSN         PIC X(44).
           05  WS-STAT-DATE        PIC 9(8).
           05  WS-STAT-TIME        PIC 9(6).
           05  FILLER              PIC X(8) VALUE SPACES.
       LINKAGE SECTION.
       01  LS-PARM.
           05  LS-PARM-LEN         PIC S9(4) COMP.
           05  LS-PARM-TEXT        PIC X(100).
       PROCEDURE DIVISION USING LS-PARM.
           MOVE SPACES TO WS-RECID WS-DSN
           IF LS-PARM-LEN > 0 AND LS-PARM-LEN <= 100
               UNSTRING LS-PARM-TEXT(1:LS-PARM-LEN) DELIMITED BY ','
                   INTO WS-RECID WS-DSN
           END-IF
           IF WS-RECID = SPACES OR WS-DSN = SPACES
              OR WS-RECID = 'CLAIMNO'
               DISPLAY 'UCFCTLU BAD PARM: NEED RECID,DATASET.NAME'
               MOVE 8 TO RETURN-CODE
               GOBACK
           END-IF
           MOVE FUNCTION CURRENT-DATE TO WS-NOW
           MOVE WS-DSN          TO WS-STAT-DSN
           MOVE WS-NOW(1:8)     TO WS-STAT-DATE
           MOVE WS-NOW(9:6)     TO WS-STAT-TIME
           OPEN I-O CTL-FILE
           IF WS-FS NOT = '00'
               DISPLAY 'UCFCTLU OPEN UCF.CTL FAILED, STATUS ' WS-FS
               MOVE 12 TO RETURN-CODE
               GOBACK
           END-IF
           MOVE WS-RECID TO CT-REC-ID
           READ CTL-FILE
           EVALUATE WS-FS
             WHEN '00'
               PERFORM FILL-RECORD
               REWRITE CT-RECORD
             WHEN '23'
               PERFORM FILL-RECORD
               WRITE CT-RECORD
             WHEN OTHER
               CONTINUE
           END-EVALUATE
           IF WS-FS NOT = '00'
               DISPLAY 'UCFCTLU UPDATE FAILED, STATUS ' WS-FS
               MOVE 12 TO RETURN-CODE
           ELSE
               DISPLAY 'UCFCTLU ' WS-RECID ' ' WS-DSN ' '
                       WS-STAT-DATE ' ' WS-STAT-TIME
           END-IF
           CLOSE CTL-FILE
           GOBACK.
       FILL-RECORD.
           MOVE WS-RECID     TO CT-REC-ID
           MOVE ZEROS        TO CT-LAST-CLAIM-ID
           MOVE WS-STAT-DATE TO CT-LAST-UPD-DATE
           MOVE 'BATCH'      TO CT-LAST-UPD-USER
           MOVE WS-STAT-DATA TO CT-DATA.
