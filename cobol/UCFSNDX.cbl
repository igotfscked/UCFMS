       IDENTIFICATION DIVISION.
       PROGRAM-ID. UCFSNDX.
      *----------------------------------------------------------*
      * UCFSNDX: STANDARD AMERICAN SOUNDEX OF A NAME.            *
      *   CALL 'UCFSNDX' USING NAME-40 CODE-4                    *
      * FIRST LETTER + 3 DIGITS (JOHN/JON/JHON = J500,           *
      * MUHAMMAD/MOHAMMED/MOHAMED = M530, SMITH/SMYTH = S530).   *
      * LETTERS ONLY: BLANKS, DIGITS AND PUNCTUATION ARE SKIPPED.*
      * A NAME WITH NO LETTERS RETURNS SPACES.                   *
      * H AND W DO NOT SEPARATE EQUAL CODES; VOWELS DO.          *
      * NO I/O, NO EXEC CICS: CALLABLE FROM BATCH, ISPF AND CICS.*
      * THE LOAD JOB (UCFSDXB) AND QUERY BOTH CALL THIS ROUTINE  *
      * SO THEIR CODES ALWAYS MATCH. COMPILE WITH RENT.          *
      *----------------------------------------------------------*
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-ALPHA        PIC X(26)
                           VALUE 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.
      *    A0 B1 C2 D3 E0 F1 G2 H* I0 J2 K2 L4 M5 N5 O0 P1 Q2 R6
      *    S2 T3 U0 V1 W* X2 Y0 Z2    (* = H/W, 0 = VOWEL)
       01  WS-DIGITS       PIC X(26)
                           VALUE '0123012*02245501262301*202'.
       01  WS-NAME         PIC X(40).
       01  WS-CODES        PIC X(40).
       01  WS-I            PIC S9(4) COMP.
       01  WS-OUT-LEN      PIC S9(4) COMP.
       01  WS-LETTER       PIC X.
       01  WS-CODE         PIC X.
       01  WS-PREV         PIC X.
       LINKAGE SECTION.
       01  LS-NAME         PIC X(40).
       01  LS-SOUNDEX      PIC X(4).
       PROCEDURE DIVISION USING LS-NAME LS-SOUNDEX.
           MOVE FUNCTION UPPER-CASE(LS-NAME) TO WS-NAME
           MOVE WS-NAME TO WS-CODES
           INSPECT WS-CODES CONVERTING WS-ALPHA TO WS-DIGITS
           MOVE SPACES TO LS-SOUNDEX
           MOVE 0 TO WS-OUT-LEN
           PERFORM VARYING WS-I FROM 1 BY 1
                   UNTIL WS-I > 40 OR WS-OUT-LEN = 4
               MOVE WS-NAME(WS-I:1)  TO WS-LETTER
               MOVE WS-CODES(WS-I:1) TO WS-CODE
               IF WS-LETTER IS ALPHABETIC-UPPER
                  AND WS-LETTER NOT = SPACE
                   IF WS-OUT-LEN = 0
                       MOVE WS-LETTER TO LS-SOUNDEX(1:1)
                       MOVE 1         TO WS-OUT-LEN
                       MOVE WS-CODE   TO WS-PREV
                   ELSE
                       EVALUATE TRUE
                         WHEN WS-CODE = '*'
                           CONTINUE
                         WHEN WS-CODE = '0'
                           MOVE '0' TO WS-PREV
                         WHEN WS-CODE = WS-PREV
                           CONTINUE
                         WHEN OTHER
                           ADD 1 TO WS-OUT-LEN
                           MOVE WS-CODE TO LS-SOUNDEX(WS-OUT-LEN:1)
                           MOVE WS-CODE TO WS-PREV
                       END-EVALUATE
                   END-IF
               END-IF
           END-PERFORM
           IF WS-OUT-LEN > 0
               PERFORM UNTIL WS-OUT-LEN = 4
                   ADD 1 TO WS-OUT-LEN
                   MOVE '0' TO LS-SOUNDEX(WS-OUT-LEN:1)
               END-PERFORM
           END-IF
           GOBACK.
