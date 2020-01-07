grammar alu;

// Hide whitespace, but don't skip it
WS : [ \n\t\r]+ -> channel(HIDDEN);
LINE_COMMENT : '//' ~[\r\n]* -> skip;
// Keywords
RELOP            : 'rel_op'; // <, >, <=, >=, ==, != Captures everything from slide 14 of salu.pdf
BOOLOP           : 'bool_op'; // !, &&, || and combinations of these (best guess for how update_lo/hi_1/2_predicate works
ARITHOP          : 'arith_op'; // Captures +/- used in slide 14 of salu.pdf
COMPUTEALU       : 'compute_alu'; // Captures everything from slide 15 of salu.pdf
// TODO: Instead of having numbered MUX, maybe implement a support one mux that
// can take variable number of arguments.
MUX5             : 'Mux5';      // 5-to-1 mux
MUX4             : 'Mux4';
MUX3             : 'Mux3';   // 3-to-1 mux
MUX2             : 'Mux2';   // 2-to-1 mux
OPT              : 'Opt';    // Pick either the argument or 0
CONSTANT         : 'C()'; // Return a finite constant
TRUE             : 'True';   // Guard corresponding to "always update"
IF               : 'if';
ELSE             : 'else';
ELIF             : 'elif';
RETURN           : 'return';
EQUAL            : '==';
GREATER          : '>';
LESS             : '<';
GREATER_OR_EQUAL : '>=';
LESS_OR_EQUAL    : '<=';
NOT_EQUAL        : '!=';
OR               : '||';
AND              : '&&';
NOT              : '!';
QUESTION         : '?';
ASSERT_FALSE      : 'assert(false);';

// Identifiers
ID : ('a'..'z' | 'A'..'Z') ('a'..'z' | 'A'..'Z' | '_' | '0'..'9')*;

// Numerical constant
NUM : ('0'..'9') | (('1'..'9')('0'..'9')+);


// alias id to state_var and packet_field
state_var    : ID;
temp_var     : ID;
packet_field : ID;
// alias id to hole variables
hole_var : ID;

// Determines whether the ALU is stateless or stateful
stateless : 'stateless';
stateful  : 'stateful';
state_indicator : 'type' ':' stateless
                | 'type' ':' stateful;

state_var_def : 'state' 'variables' ':' '{' state_var_seq '}';

state_var_seq : /* epsilon */
              | state_vars
              ;

state_vars : state_var                  #SingleStateVar
           | state_var ',' state_vars   #MultipleStateVars
           ;

hole_def : 'hole' 'variables' ':' '{' hole_seq '}';

hole_seq : /* epsilon */
         | hole_vars
         ;

hole_vars : hole_var                 #SingleHoleVar
          | hole_var ',' hole_vars   #MultipleHoleVars
          ;

packet_field_def : 'packet' 'fields' ':' '{' packet_field_seq '}';
packet_field_seq : /* epsilon */
                 | packet_fields
                 ;

packet_fields : packet_field                    #SinglePacketField
              | packet_field ',' packet_fields  #MultiplePacketFields
              ;

// alu_body
alu_body : statement+;

condition_block : '(' expr ')' '{' alu_body '}';

statement : variable '=' expr ';'        #StmtUpdateExpr
          | 'int ' temp_var '=' expr ';' #StmtUpdateTempInt
          | 'bit ' temp_var '=' expr ';' #StmtUpdateTempBit
          // NOTE: Having multiple return statements between a pair of curly
          // braces is syntactically correct, but such program might not make
          // sense for us.
          // TODO: Modify the generator to catch multiple return statements
          // and output errors early on.
          | return_statement #StmtReturn
          | IF condition_block (ELIF condition_block)* (ELSE  '{' else_body = alu_body '}')? #StmtIfElseIfElse
          | ASSERT_FALSE #AssertFalse
          ;

return_statement : RETURN expr ';';

variable : ID ;
expr   : variable #Var
       | expr op=('+'|'-'|'*'|'/') expr #ExprWithOp
       | '(' expr ')' #ExprWithParen
       | NUM #Num
       | expr EQUAL expr #Equals
       | expr GREATER expr #Greater
       | expr GREATER_OR_EQUAL expr #GreaterEqual
       | expr LESS expr #Less
       | expr LESS_OR_EQUAL expr #LessEqual
       | expr NOT_EQUAL expr #NotEqual
       | expr AND expr #And
       | expr OR expr #Or
       | NOT expr #NOT
       | TRUE #True
       | expr '?' expr ':' expr #Ternary
       // Currently, we use below rules only from stateful ALUs.
       | MUX2 '(' expr ',' expr ')' #Mux2
       | MUX3 '(' expr ',' expr ',' NUM ')' #Mux3WithNum
       | MUX3 '(' expr ',' expr ',' expr ')' #Mux3
       | MUX4 '(' expr ',' expr ',' expr ',' expr ')' #Mux4
       | MUX5 '(' expr ',' expr ',' expr ',' expr ',' expr ')' #Mux5
       | OPT '(' expr ')' #Opt
       | CONSTANT #Constant
       | ARITHOP '(' expr ',' expr ')' # ArithOp
       | COMPUTEALU '(' expr ',' expr ')' # ComputeAlu
       | RELOP '(' expr ',' expr ')' #RelOp
       | BOOLOP '(' expr ',' expr ')' #BoolOp
       ;

alu: state_indicator state_var_def hole_def packet_field_def alu_body;
