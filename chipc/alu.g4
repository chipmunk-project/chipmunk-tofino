grammar alu;

// Hide whitespace, but don't skip it
WS : [ \n\t\r]+ -> channel(HIDDEN);
LINE_COMMENT : '//' ~[\r\n]* -> skip;
// Keywords
RELOP            : 'rel_op'; // <, >, <=, >=, ==, != Captures everything from slide 14 of salu.pdf
BOOLOP           : 'boolean_op'; // !, &&, || and combiations of these (best guess for how update_lo/hi_1/2_predicate works
ARITHOP          : 'arith_op'; // Captures +/- used in slide 14 of salu.pdf
COMPUTEALU       : 'compute_alu'; // Captures everything from slide 15 of salu.pdf
MUX5             : 'Mux5';      // 5-to-1 mux
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
BITOR            : '|';
NOT              : '!';

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

// list of state_var
state_var_with_comma : ',' state_var;
state_vars : 'state' 'variables' ':' '{' '}'
           | 'state' 'variables' ':' '{' state_var '}'
           | 'state' 'variables' ':' '{' state_var state_var_with_comma+ '}';

hole_var_with_comma : ',' hole_var;
hole_vars : 'hole' 'variables' ':' '{' '}'
          | 'hole' 'variables' ':' '{' hole_var '}'
          | 'hole' 'variables' ':' '{' hole_var hole_var_with_comma+ '}'
          ;

// list of packet_field
packet_field_with_comma : ',' packet_field;
packet_fields : 'packet' 'fields' ':' '{' packet_field '}'
              | 'packet' 'fields' ':' '{' packet_field packet_field_with_comma+ '}';


// guard for if and elif statements
guard  : guard (EQUAL
              | GREATER
              | GREATER_OR_EQUAL
              | LESS
              | LESS_OR_EQUAL
              | NOT_EQUAL
              | AND
              | OR
              | BITOR
              | NOT) guard #Nested
       | '(' guard ')' #Paren
       | RELOP '(' expr ',' expr ')' #RelOp
       | BOOLOP '(' guard ',' guard ')' #BoolOp
       | expr EQUAL expr #Equals
       | expr GREATER expr #Greater
       | expr GREATER_OR_EQUAL expr #GreaterEqual
       | expr LESS expr #Less
       | expr LESS_OR_EQUAL expr #LessEqual
       | expr NOT_EQUAL expr #NotEqual
       | expr AND expr #And
       | expr OR expr #Or
       | expr BITOR expr #BitOr
       | NOT expr #NOT
       | TRUE #True
       | ID #bool_var
       ;


// alu_body
alu_body : alu_update = updates
         | return_update = return_statement
         | IF '(' if_guard = guard ')' '{' if_body =  alu_body '}' (ELIF '(' elif_guard = guard ')' '{' elif_body = alu_body '}')* (ELSE  '{' else_body = alu_body '}')?
         ;

return_statement : RETURN expr ';'
                 | RETURN guard ';';


updates: update+;
update : state_var '=' expr ';'
       | state_var '=' guard ';'
       | 'int ' temp_var '=' expr ';'
       | 'bit ' temp_var '=' guard ';'
       ;

variable : ID ;
expr   : variable #Var
       | expr op=('+'|'-'|'*'|'/') expr #ExprWithOp
       | '(' expr ')' #ExprWithParen
       | MUX3 '(' expr ',' expr ',' NUM ')' #Mux3WithNum
       | MUX3 '(' expr ',' expr ',' expr ')' #Mux3
       | MUX5 '(' expr ',' expr ',' expr ',' expr ',' expr ')' #Mux5
       | MUX2 '(' expr ',' expr ')' #Mux2
       | OPT '(' expr ')' #Opt
       | CONSTANT #Constant
       | ARITHOP '(' expr ',' expr ')' # ArithOp
       | NUM #Value
       | COMPUTEALU '(' expr ',' expr ')' # ComputeAlu
       ;

alu: state_indicator state_vars hole_vars packet_fields alu_body;
