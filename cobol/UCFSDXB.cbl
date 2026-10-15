       IDENTIFICATION DIVISION.
       PROGRAM-ID. UCFSDXB.
      *----------------------------------------------------------*
      * UCFSDXB: BUILD THE SOUNDEX LOOKUP RECORDS (BATCH).       *
      * READS THE OWNER KSDS IN KEY ORDER AND WRITES ONE 70-BYTE *
      * RECORD PER OWNER RECORD:                                 *
      *   1-4   SOUNDEX(OWNERLASTNAME) FROM UCFSNDX              *
      *   5-70  66-BYTE OWNER KEY (LAST NAME 40 + PROPERTY ID 26)*
      * NAMES WITH NO LETTERS ARE SKIPPED. THE OUTPUT IS SORTED  *
      * ON BYTES 1-70 AND LOADED INTO THE LOOKUP KSDS BY UCFSDX. *
      * RETURN CODE 0 OK, 12 ON ANY FILE ERROR.                  *
      *----------------------------------------------------------*
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT OWNER-FILE ASSIGN TO OWNER
               ORGANIZATION IS INDEXED
               ACCESS MODE IS SEQUENTIAL
               RECORD KEY IS OWN-KEY
               FILE STATUS IS WS-OWN-FS.
           SELECT SDX-FILE ASSIGN TO SDXOUT
               ORGANIZATION IS SEQUENTIAL
               FILE STATUS IS WS-SDX-FS.
       DATA DIVISION.
       FILE SECTION.
       FD  OWNER-FILE.
       01  OWN-REC.
           05  OWN-KEY.
               10  OWN-LAST-NAME      PIC X(40).
               10  OWN-PROPERTY-ID    PIC X(26).
           05  OWN-TAPE-REC           PIC X(469).
       FD  SDX-FILE
           RECORDING MODE IS F.
       01  SDX-REC.
           05  SDX-CODE               PIC X(4).
           05  SDX-OWNER-KEY          PIC X(66).
       WORKING-STORAGE SECTION.
       01  WS-OWN-FS               PIC XX.
       01  WS-SDX-FS               PIC XX.
       01  WS-EOF                  PIC X VALUE 'N'.
       01  WS-CODE                 PIC X(4).
       01  WS-READ                 PIC 9(9) VALUE 0.
       01  WS-WRITTEN              PIC 9(9) VALUE 0.
       01  WS-SKIPPED              PIC 9(9) VALUE 0.
       PROCEDURE DIVISION.
           OPEN INPUT OWNER-FILE
           IF WS-OWN-FS NOT = '00'
               DISPLAY 'UCFSDXB OPEN OWNER FAILED, STATUS ' WS-OWN-FS
               MOVE 12 TO RETURN-CODE
               GOBACK
           END-IF
           OPEN OUTPUT SDX-FILE
           IF WS-SDX-FS NOT = '00'
               DISPLAY 'UCFSDXB OPEN SDXOUT FAILED, STATUS ' WS-SDX-FS
               CLOSE OWNER-FILE
               MOVE 12 TO RETURN-CODE
               GOBACK
           END-IF
           PERFORM UNTIL WS-EOF = 'Y'
               READ OWNER-FILE
                   AT END
                       MOVE 'Y' TO WS-EOF
                   NOT AT END
                       ADD 1 TO WS-READ
                       CALL 'UCFSNDX' USING OWN-LAST-NAME WS-CODE
                       IF WS-CODE = SPACES
                           ADD 1 TO WS-SKIPPED
                       ELSE
                           MOVE WS-CODE TO SDX-CODE
                           MOVE OWN-KEY TO SDX-OWNER-KEY
                           WRITE SDX-REC
                           IF WS-SDX-FS NOT = '00'
                               DISPLAY 'UCFSDXB WRITE FAILED, STATUS '
                                       WS-SDX-FS
                               MOVE 12 TO RETURN-CODE
                               MOVE 'Y' TO WS-EOF
                           END-IF
                           ADD 1 TO WS-WRITTEN
                       END-IF
               END-READ
               IF WS-OWN-FS NOT = '00' AND WS-OWN-FS NOT = '10'
                   DISPLAY 'UCFSDXB READ FAILED, STATUS ' WS-OWN-FS
                   MOVE 12 TO RETURN-CODE
                   MOVE 'Y' TO WS-EOF
               END-IF
           END-PERFORM
           CLOSE OWNER-FILE SDX-FILE
           DISPLAY 'UCFSDXB OWNER RECORDS READ    ' WS-READ
           DISPLAY 'UCFSDXB SOUNDEX RECORDS OUT   ' WS-WRITTEN
           DISPLAY 'UCFSDXB SKIPPED (NO LETTERS)  ' WS-SKIPPED
           GOBACK.
