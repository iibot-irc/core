#!/usr/bin/env /scratch/m4burns/racket/bin/racket
#lang racket
(require racket/sandbox
         racket/serialize
         racket/tcp
         racket/async-channel
         net/base64)

(define namespace-store "/users/cscbot/state/racketi/namespaces")

(define (serialize-namespace ns port)
  (write
    (serialize
      (filter-map
        (lambda(sym)
          (with-handlers
              ([exn:fail:contract:variable? (lambda(e) #f)]
               [exn:fail:syntax? (lambda(e) #f)])
            (let ((val (namespace-variable-value sym #t #f ns)))
              (if (serializable? val) (cons sym val) #f))))
        (namespace-mapped-symbols ns)))
    port))

(define (unserialize-namespace ns port)
  (for-each
    (lambda(cell)
      (namespace-set-variable-value! (car cell) (cdr cell) #t ns))
    (deserialize (read port))))

(define (main)
  (define (make-empty-sandbox shared)
    (parameterize
      ([sandbox-output 'pipe]
       [sandbox-error-output #f]
       [sandbox-propagate-breaks #f]
       [sandbox-memory-limit 128]
       [sandbox-eval-limits '(5 128)])
      (define sandbox (make-evaluator 'racket))
      (sandbox `(define share-sandbox (make-parameter ,shared)))
      (cons (make-semaphore 1) sandbox)))
  (define (read-stored-namespaces)
    (define (file->sandbox file)
      (with-handlers
        ([exn? (lambda(e) (fprintf (current-error-port)
                                   "Couldn't read namespace ~a: ~a~n"
                                   file (exn-message e))
                          #f)])
        (call-with-input-file
          file
          (lambda(port)
            (define shared (read port))
            (unless (boolean? shared)
              (raise (exn:fail:contract "Shared flag missing from namespace file."
                                        (current-continuation-marks))))
            (define sandbox (make-empty-sandbox shared))
            (unserialize-namespace ((cdr sandbox) '(current-namespace))
                                   port)
            sandbox))))
    (foldl
      (lambda(dirent world)
        (if (file-exists? dirent)
            (let ((sandbox (file->sandbox dirent)))
              (if sandbox
                  (hash-set world
                            (bytes->string/utf-8
                              (base64-decode
                                (string->bytes/utf-8
                                  (let-values (((base name _) (split-path dirent)))
                                    (path->string name)))))
                            sandbox)
                  world))
            world))
      (make-immutable-hash)
      (directory-list namespace-store #:build? #t)))
  (define (make-namespace-serialization-channel)
    (define channel (make-async-channel))
    (thread
      (thunk
        (let loop ()
          (match (async-channel-get channel)
            [`(,(? string? name) ,(? boolean? shared) ,(? namespace? ns))
             (call-with-output-file
               (build-path namespace-store
                           (bytes->string/utf-8
                             (base64-encode
                               (string->bytes/utf-8 name)
                               #"")))
               (lambda(port)
                 (write shared port)
                 (serialize-namespace ns port))
               #:exists 'replace)
             (loop)]
            [else
              (fprintf (current-error-port) "Warning: bad message in namespace serialization thread.~n")
              (loop)]))))
    channel)
  (define (eval-in-sandbox sandbox target check-perm expr out serialization-channel)
    (call-with-semaphore (car sandbox)
      (thunk
        (with-handlers ([exn? (lambda(e) (void))])
          (with-handlers
            ([exn:fail?
              (lambda(e)
                (fprintf out "~a~n" (exn-message e))
                (close-output-port out))])
            (when
              (and check-perm
                    (not ((cdr sandbox) '(if (parameter? share-sandbox) (share-sandbox) #f))))
              (raise (exn:fail:contract "You don't have permission to use this sandbox."
                                        (current-continuation-marks))))
            (define courier
              (thread
                (thunk
                  (copy-port (get-output (cdr sandbox)) out))))
            (write ((cdr sandbox) expr) out)
            (newline out)
            (unless (sync/timeout 0.5 courier)
              (kill-thread courier))
            (close-output-port out)
            (with-handlers
              ([exn:fail?
                  (lambda(e) (fprintf (current-error-port) "~a~n" (exn-message e)))])
              (async-channel-put serialization-chan
                                  (list target
                                        ((cdr sandbox) '(if (parameter? share-sandbox) (share-sandbox) #f))
                                        ((cdr sandbox) '(current-namespace))))))))))
  (define (serve-client in out world serialization-channel)
    (with-handlers ([exn:break? raise]
                    [exn? (lambda(e) world)])
      (with-handlers
        ([(lambda(e) (or (exn:fail:network? e) (exn:fail:resource? e)))
          (lambda(e)
            (tcp-abandon-port in)
            (tcp-abandon-port out)
            world)]
         [exn:fail?
           (lambda(e)
             (write-string (exn-message e) out)
             (close-input-port in)
             (close-output-port out))])
        (define-values
          (nick ns expr)
          (call-with-limits 30 128
            (thunk
              (match (port->string in)
                [(pregexp #px"^[ \t\r\n\v\f]*([^ \t\r\n\v\f]+)[ \t\r\n\v\f]*(eval in[ \t\r\n\v\f]*[^ \t\r\n\v\f]+)?[ \t\r\n\v\f]*(.*)$"
                          (list _ nick (or (pregexp #px"^eval in[ \t\r\n\v\f]*([^ \t\r\n\v\f]+)$" (list _ ns)) ns) expr))
                 (values nick ns expr)]
                [else (raise (exn:fail:contract "Invalid input." (current-continuation-marks)))]))))
        (close-input-port in)
        (define target (if ns ns nick))
        (define require-permission (and ns (not (string=? ns nick))))
        (cond
          [(and
             (hash-has-key? world target)
             (evaluator-alive? (cdr (hash-ref world target))))
           (thread
             (thunk
               (eval-in-sandbox
                 (hash-ref world target)
                 target
                 require-permission
                 expr
                 out
                 serialization-channel)))
           world]
          [else
            (define new-sandbox (make-empty-sandbox require-permission))
            (fprintf out "~a: Sandbox prepared for ~a.~n" nick target)
            (thread
             (thunk
               (eval-in-sandbox
                 new-sandbox
                 target
                 require-permission
                 expr
                 out
                 serialization-channel)))
            (hash-set world target new-sandbox)]))))

  (define listener (tcp-listen 5555 4 #t "127.0.0.1"))
  (define serialization-chan (make-namespace-serialization-channel))
  (with-handlers
    ([exn:break? (lambda(e) (fprintf (current-error-port) "~nTerminating on break.~n"))])
    (let loop ((world (read-stored-namespaces)))
      (match (sync/enable-break (tcp-accept-evt listener))
        [`(,(? port? in) ,(? port? out))
          (loop (serve-client in out world serialization-chan))]
        [else
          (fprintf (current-error-port) "Warning: Couldn't accept connection.~n")
          (loop world)])))
  (tcp-close listener))

(main)
